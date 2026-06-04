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
    )


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
