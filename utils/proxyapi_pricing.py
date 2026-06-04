"""Парсинг тарифов с https://proxyapi.ru/pricing и загрузка в JSON."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PRICING_URL = "https://proxyapi.ru/pricing"
PRICE_ROW_RE = re.compile(
    r'shrink-0">([^<]+)</span>.*?font-medium">([\d\s\u00a0,]+)\s*₽',
    re.DOTALL,
)

# Если модели нет на странице pricing — ближайший аналог.
MODEL_ALIASES: dict[str, str] = {
    "gpt-5-mini-2025-08-07": "gpt-5.4-mini",
    "gpt-5-mini": "gpt-5.4-mini",
}


@dataclass(frozen=True)
class ModelPricing:
    input_rub_per_1m: float
    output_rub_per_1m: float
    image_input_rub_per_1m: float = 0.0
    cache_read_rub_per_1m: float | None = None


class ProxyApiPricingStore:
    def __init__(self, pricing_file: Path) -> None:
        self._path = pricing_file
        self._models: dict[str, ModelPricing] = {}
        self._fetched_at: str | None = None
        if self._path.exists():
            self._load_file()

    @property
    def fetched_at(self) -> str | None:
        return self._fetched_at

    def get(self, model_id: str) -> ModelPricing | None:
        key = MODEL_ALIASES.get(model_id, model_id)
        return self._models.get(key)

    async def refresh_from_site(self) -> dict[str, Any]:
        html = await fetch_pricing_html()
        payload = build_pricing_payload(parse_pricing_html(html))
        self._apply_payload(payload)
        self._save_file(payload)
        logger.info(
            "Тарифы ProxyAPI обновлены: %d моделей",
            len(payload.get("models", {})),
        )
        return payload

    def _apply_payload(self, payload: dict[str, Any]) -> None:
        self._fetched_at = payload.get("fetched_at")
        models: dict[str, ModelPricing] = {}
        for model_id, raw in payload.get("models", {}).items():
            if not isinstance(raw, dict):
                continue
            try:
                models[model_id] = ModelPricing(
                    input_rub_per_1m=float(raw["input_rub_per_1m"]),
                    output_rub_per_1m=float(raw["output_rub_per_1m"]),
                    image_input_rub_per_1m=float(
                        raw.get("image_input_rub_per_1m", 0) or 0
                    ),
                    cache_read_rub_per_1m=(
                        float(raw["cache_read_rub_per_1m"])
                        if raw.get("cache_read_rub_per_1m") is not None
                        else None
                    ),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Пропуск модели %s: %s", model_id, exc)
        self._models = models

    def _load_file(self) -> None:
        try:
            with self._path.open(encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Не удалось загрузить %s: %s", self._path, exc)
            return
        self._apply_payload(payload)

    def _save_file(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)


async def fetch_pricing_html(url: str = PRICING_URL) -> str:
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def parse_pricing_html(html: str) -> dict[str, dict[str, float]]:
    """Извлекает тарифы ₽/1M по моделям из HTML страницы pricing."""
    models: dict[str, dict[str, float]] = {}
    parts = html.split('tracking-tight font-medium">')

    for part in parts[1:]:
        model_id = part.split("</div>", 1)[0].strip()
        if not model_id or len(model_id) > 80:
            continue

        chunk = part[:12_000]
        rates: dict[str, float] = {}

        for label, raw_price in PRICE_ROW_RE.findall(chunk):
            value = _parse_rub_amount(raw_price)
            normalized = label.strip().lower()

            if normalized == "ввод":
                rates["input_rub_per_1m"] = value
            elif normalized == "вывод":
                rates["output_rub_per_1m"] = value
            elif "изображение" in normalized and "ввод" in normalized:
                rates["image_input_rub_per_1m"] = value
            elif normalized == "кэш чтение":
                rates["cache_read_rub_per_1m"] = value

        if "input_rub_per_1m" in rates and "output_rub_per_1m" in rates:
            models[model_id] = rates

    return models


def build_pricing_payload(models: dict[str, dict[str, float]]) -> dict[str, Any]:
    return {
        "source": PRICING_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "currency": "RUB",
        "unit": "per_1M_tokens",
        "models": models,
        "aliases": MODEL_ALIASES,
    }


def _parse_rub_amount(text: str) -> float:
    cleaned = (
        text.replace("\u00a0", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )
    return float(cleaned)
