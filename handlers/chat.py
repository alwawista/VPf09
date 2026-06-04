"""Обработка текстовых сообщений пользователя."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from handlers.image import generate_from_prompt
from memory import BRANCH_IMAGE, ChatMemory
from utils.image_service import ImageGenerationService
from utils.openai_client import OpenAIChatService
from utils.prompts import PromptManager

router = Router(name="chat")
logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4096


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(
    message: Message,
    memory: ChatMemory,
    prompts: PromptManager,
    openai_service: OpenAIChatService,
    image_service: ImageGenerationService,
) -> None:
    if message.chat is None or not message.text:
        return

    user_text = message.text.strip()
    if not user_text:
        await message.answer("Напиши текстовое сообщение.")
        return

    chat_id = message.chat.id

    if memory.get_branch(chat_id) == BRANCH_IMAGE:
        await generate_from_prompt(message, image_service, user_text)
        return
    mode_id = memory.get_mode(chat_id)
    history = memory.build_context_messages(chat_id)

    await message.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        answer = await openai_service.complete(mode_id, history, user_text)
    except RuntimeError as exc:
        logger.exception("Ошибка при запросе к LLM")
        await message.answer(str(exc))
        return
    except Exception:
        logger.exception("Неожиданная ошибка")
        await message.answer(
            "Не удалось получить ответ. Проверьте PROXY_API_KEY и доступность ProxyAPI."
        )
        return

    memory.add_exchange(chat_id, user_text, answer)

    for chunk in _split_message(answer):
        await message.answer(chunk)


def _split_message(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks or [text[:limit]]
