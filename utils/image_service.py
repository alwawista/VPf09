"""Генерация изображений через ProxyAPI (gpt-image-2)."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any

from openai import APIStatusError, AsyncOpenAI

from config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageGenerationResult:
    image_bytes: bytes
    usage_summary: str


class ImageGenerationService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.proxy_api_key,
            base_url=settings.openai_base_url,
        )

    async def generate(self, prompt: str) -> ImageGenerationResult:
        logger.info(
            "Запрос изображения: model=%s size=%s prompt_len=%d",
            self._settings.image_model,
            self._settings.image_size,
            len(prompt),
        )

        try:
            response = await self._client.images.generate(
                model=self._settings.image_model,
                prompt=prompt,
                size=self._settings.image_size,
                quality=self._settings.image_quality,
                n=1,
            )
        except APIStatusError as exc:
            logger.exception("Ошибка Images API")
            raise RuntimeError(
                f"Images API ({exc.status_code}): {exc.message}"
            ) from exc

        image_bytes = _extract_image_bytes(response)
        usage_summary = _format_usage(getattr(response, "usage", None))
        logger.info("Изображение получено: %d байт", len(image_bytes))
        return ImageGenerationResult(
            image_bytes=image_bytes,
            usage_summary=usage_summary,
        )


def _extract_image_bytes(response: Any) -> bytes:
    if not response.data:
        raise RuntimeError("API не вернул данные изображения.")

    item = response.data[0]
    if getattr(item, "b64_json", None):
        return base64.b64decode(item.b64_json)

    if getattr(item, "url", None):
        raise RuntimeError(
            "API вернул URL вместо b64_json. Укажите response_format или проверьте модель."
        )

    raise RuntimeError("Не удалось извлечь изображение из ответа API.")


def _format_usage(usage: Any) -> str:
    if usage is None:
        return ""

    parts: list[str] = []
    mapping = (
        ("input_tokens", "ввод"),
        ("output_tokens", "вывод"),
        ("total_tokens", "всего"),
        ("input_tokens_details", None),
    )
    for field, label in mapping:
        if label is None:
            continue
        value = getattr(usage, field, None)
        if value is not None:
            parts.append(f"{label}: {value}")

    details = getattr(usage, "input_tokens_details", None)
    if details is not None:
        text_tokens = getattr(details, "text_tokens", None)
        image_tokens = getattr(details, "image_tokens", None)
        if text_tokens is not None:
            parts.append(f"текст (ввод): {text_tokens}")
        if image_tokens is not None:
            parts.append(f"изображение (ввод): {image_tokens}")

    if not parts:
        return ""
    return "Токены: " + ", ".join(parts)
