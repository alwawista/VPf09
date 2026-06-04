"""Загрузка настроек из переменных окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OPENAI_BASE_URL = "https://api.proxyapi.ru/openai/v1"
DEFAULT_CHAT_MODEL = "gpt-5-mini-2025-08-07"
DEFAULT_IMAGE_MODEL = "gpt-image-2"
DEFAULT_IMAGE_SIZE = "1024x1024"
DEFAULT_IMAGE_QUALITY = "auto"
# Тарифы ProxyAPI, ₽ за 1M токенов (см. https://proxyapi.ru/pricing )
DEFAULT_CHAT_INPUT_PRICE_RUB_PER_1M = 230.0
DEFAULT_CHAT_OUTPUT_PRICE_RUB_PER_1M = 1370.0
DEFAULT_IMAGE_INPUT_PRICE_RUB_PER_1M = 1520.0
DEFAULT_IMAGE_OUTPUT_PRICE_RUB_PER_1M = 9100.0
DEFAULT_IMAGE_IMAGE_INPUT_PRICE_RUB_PER_1M = 2430.0
DEFAULT_CBR_JSON_URL = "https://www.cbr-xml-daily.ru/daily_json.js"

load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    proxy_api_key: str
    openai_base_url: str
    chat_model: str
    image_model: str
    image_size: str
    image_quality: str
    memory_max_messages: int
    memory_file: Path
    prompts_file: Path
    telegram_connect_timeout: float
    chat_input_price_rub_per_1m: float
    chat_output_price_rub_per_1m: float
    image_input_price_rub_per_1m: float
    image_output_price_rub_per_1m: float
    image_image_input_price_rub_per_1m: float
    cbr_json_url: str
    pricing_file: Path
    pricing_fetch_on_start: bool


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    proxy_api_key = os.getenv("PROXY_API_KEY", "").strip()
    openai_base_url = (
        os.getenv("OPENAI_BASE_URL", "").strip() or DEFAULT_OPENAI_BASE_URL
    )
    chat_model = os.getenv("CHAT_MODEL", DEFAULT_CHAT_MODEL).strip()
    image_model = os.getenv("IMAGE_MODEL", DEFAULT_IMAGE_MODEL).strip()
    image_size = os.getenv("IMAGE_SIZE", DEFAULT_IMAGE_SIZE).strip()
    image_quality = os.getenv("IMAGE_QUALITY", DEFAULT_IMAGE_QUALITY).strip()
    memory_max_messages = _get_int_env("MEMORY_MAX_MESSAGES", 5)
    memory_file = BASE_DIR / os.getenv("MEMORY_FILE", "chat_memory.json").strip()
    prompts_file = BASE_DIR / os.getenv("PROMPTS_FILE", "prompts.json").strip()
    telegram_connect_timeout = _get_float_env("TELEGRAM_CONNECT_TIMEOUT", 30.0)
    chat_input_price_rub_per_1m = _get_float_env(
        "CHAT_INPUT_PRICE_RUB_PER_1M", DEFAULT_CHAT_INPUT_PRICE_RUB_PER_1M
    )
    chat_output_price_rub_per_1m = _get_float_env(
        "CHAT_OUTPUT_PRICE_RUB_PER_1M", DEFAULT_CHAT_OUTPUT_PRICE_RUB_PER_1M
    )
    image_input_price_rub_per_1m = _get_float_env(
        "IMAGE_INPUT_PRICE_RUB_PER_1M", DEFAULT_IMAGE_INPUT_PRICE_RUB_PER_1M
    )
    image_output_price_rub_per_1m = _get_float_env(
        "IMAGE_OUTPUT_PRICE_RUB_PER_1M", DEFAULT_IMAGE_OUTPUT_PRICE_RUB_PER_1M
    )
    image_image_input_price_rub_per_1m = _get_float_env(
        "IMAGE_IMAGE_INPUT_PRICE_RUB_PER_1M", DEFAULT_IMAGE_IMAGE_INPUT_PRICE_RUB_PER_1M
    )
    cbr_json_url = (
        os.getenv("CBR_JSON_URL", "").strip() or DEFAULT_CBR_JSON_URL
    )
    pricing_file = BASE_DIR / os.getenv(
        "PRICING_FILE", "proxyapi_pricing.json"
    ).strip()
    pricing_fetch_on_start = _get_bool_env("PRICING_FETCH_ON_START", True)

    missing = []
    if not bot_token:
        missing.append("BOT_TOKEN")
    if not proxy_api_key:
        missing.append("PROXY_API_KEY")
    if missing:
        raise RuntimeError(
            f"Не заданы обязательные переменные окружения: {', '.join(missing)}"
        )

    return Settings(
        bot_token=bot_token,
        proxy_api_key=proxy_api_key,
        openai_base_url=openai_base_url,
        chat_model=chat_model,
        image_model=image_model,
        image_size=image_size,
        image_quality=image_quality,
        memory_max_messages=memory_max_messages,
        memory_file=memory_file,
        prompts_file=prompts_file,
        telegram_connect_timeout=telegram_connect_timeout,
        chat_input_price_rub_per_1m=chat_input_price_rub_per_1m,
        chat_output_price_rub_per_1m=chat_output_price_rub_per_1m,
        image_input_price_rub_per_1m=image_input_price_rub_per_1m,
        image_output_price_rub_per_1m=image_output_price_rub_per_1m,
        image_image_input_price_rub_per_1m=image_image_input_price_rub_per_1m,
        cbr_json_url=cbr_json_url,
        pricing_file=pricing_file,
        pricing_fetch_on_start=pricing_fetch_on_start,
    )


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} должно быть целым числом") from exc
    if parsed < 1:
        raise RuntimeError(f"{name} должно быть >= 1")
    return parsed


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} должно быть числом") from exc
