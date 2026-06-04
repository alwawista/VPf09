"""Курс USD/RUB с данными ЦБ (JSON-зеркало cbr-xml-daily.ru)."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_CBR_JSON_URL = "https://www.cbr-xml-daily.ru/daily_json.js"


class CbrRateService:
    """Кэширует курс USD на несколько минут."""

    def __init__(
        self,
        json_url: str = DEFAULT_CBR_JSON_URL,
        cache_ttl_sec: int = 300,
    ) -> None:
        self._json_url = json_url
        self._cache_ttl_sec = cache_ttl_sec
        self._cached_usd_rub: float | None = None
        self._cached_at: float = 0.0

    async def get_usd_rub(self) -> float:
        now = time.monotonic()
        if (
            self._cached_usd_rub is not None
            and now - self._cached_at < self._cache_ttl_sec
        ):
            return self._cached_usd_rub

        rate = await self._fetch_usd_rub()
        self._cached_usd_rub = rate
        self._cached_at = now
        logger.info("Курс ЦБ USD/RUB: %.4f", rate)
        return rate

    async def _fetch_usd_rub(self) -> float:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self._json_url)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Не удалось получить курс ЦБ: %s", exc)
            raise RuntimeError(
                "Не удалось загрузить курс USD с API ЦБ. Попробуйте позже."
            ) from exc

        usd = _extract_usd_value(data)
        if usd <= 0:
            raise RuntimeError("Некорректный курс USD в ответе ЦБ.")
        return usd


def _extract_usd_value(data: Any) -> float:
    valute = data.get("Valute") if isinstance(data, dict) else None
    if not isinstance(valute, dict):
        raise ValueError("Нет блока Valute в ответе ЦБ")

    usd = valute.get("USD")
    if not isinstance(usd, dict):
        raise ValueError("Нет USD в ответе ЦБ")

    raw = usd.get("Value") or usd.get("value")
    if raw is None:
        raise ValueError("Нет поля Value для USD")

    if isinstance(raw, (int, float)):
        return float(raw)

    text = str(raw).strip().replace(",", ".")
    return float(text)
