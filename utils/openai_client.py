"""Клиент OpenAI через ProxyAPI."""

from __future__ import annotations

import logging
from typing import Any

from openai import APIStatusError, AsyncOpenAI

from config import Settings
from memory import ChatMessage
from utils.prompts import PromptManager

logger = logging.getLogger(__name__)


class OpenAIChatService:
    def __init__(self, settings: Settings, prompts: PromptManager) -> None:
        self._settings = settings
        self._prompts = prompts
        self._client = AsyncOpenAI(
            api_key=settings.proxy_api_key,
            base_url=settings.openai_base_url,
        )

    async def complete(
        self,
        mode_id: str,
        history: list[ChatMessage],
        user_text: str,
    ) -> str:
        system_prompt = self._prompts.get_system_prompt(mode_id)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_text},
        ]

        try:
            response = await self._client.chat.completions.create(
                model=self._settings.chat_model,
                messages=messages,
            )
        except APIStatusError as exc:
            logger.exception("Ошибка OpenAI API")
            raise RuntimeError(
                f"OpenAI API ({exc.status_code}): {exc.message}"
            ) from exc

        content = response.choices[0].message.content
        return (content or "").strip() or "Пустой ответ от модели."
