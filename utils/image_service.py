"""Генерация изображений через ProxyAPI (gpt-image-2)."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any

from openai import APIStatusError, AsyncOpenAI

from config import Settings
from utils.cost_calculator import CostCalculator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageGenerationResult:
    image_bytes: bytes
    cost_footer: str


class ImageGenerationService:
    def __init__(
        self,
        settings: Settings,
        cost_calculator: CostCalculator,
    ) -> None:
        self._settings = settings
        self._cost = cost_calculator
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

        cost_footer = ""
        try:
            breakdown = await self._cost.from_image_usage(response.usage)
            cost_footer = await self._cost.format_footer(breakdown)
        except Exception:
            logger.exception("Не удалось рассчитать стоимость image-запроса")

        logger.info("Изображение получено: %d байт", len(image_bytes))
        return ImageGenerationResult(
            image_bytes=image_bytes,
            cost_footer=cost_footer,
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
