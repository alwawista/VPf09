"""Клиент OpenAI через ProxyAPI."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from openai import APIStatusError, AsyncOpenAI

from config import Settings
from memory import ChatMessage
from utils.cost_calculator import CostCalculator
from utils.prompts import PromptManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatCompletionResult:
    text: str
    cost_footer: str


class OpenAIChatService:
    def __init__(
        self,
        settings: Settings,
        prompts: PromptManager,
        cost_calculator: CostCalculator,
    ) -> None:
        self._settings = settings
        self._prompts = prompts
        self._cost = cost_calculator
        self._client = AsyncOpenAI(
            api_key=settings.proxy_api_key,
            base_url=settings.openai_base_url,
        )

    async def complete(
        self,
        mode_id: str,
        history: list[ChatMessage],
        user_text: str,
    ) -> ChatCompletionResult:
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

        content = (response.choices[0].message.content or "").strip()
        text = content or "Пустой ответ от модели."

        cost_footer = ""
        try:
            breakdown = await self._cost.from_chat_usage(response.usage)
            cost_footer = await self._cost.format_footer(breakdown)
        except Exception:
            logger.exception("Не удалось рассчитать стоимость chat-запроса")

        return ChatCompletionResult(text=text, cost_footer=cost_footer)
