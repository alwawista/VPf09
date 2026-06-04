"""
Точка входа Telegram-бота (aiogram 3 + ProxyAPI / OpenAI).

Структура:
  config.py   — настройки из .env
  memory.py   — память диалога по chat_id
  prompts.json — режимы (system prompts)
  handlers/   — команды и сообщения
  utils/      — промпты и OpenAI-клиент
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from config import Settings, get_settings
from handlers import register_handlers
from memory import ChatMemory
from utils.image_service import ImageGenerationService
from utils.openai_client import OpenAIChatService
from utils.prompts import PromptManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_bot(settings: Settings) -> Bot:
    session = AiohttpSession(timeout=settings.telegram_connect_timeout)
    return Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(settings: Settings) -> Dispatcher:
    prompts = PromptManager(settings.prompts_file)
    memory = ChatMemory(
        storage_path=settings.memory_file,
        default_mode=prompts.default_mode,
        max_messages=settings.memory_max_messages,
    )
    openai_service = OpenAIChatService(settings, prompts)
    image_service = ImageGenerationService(settings)

    logger.info(
        "Бот готов: chat=%s, image=%s, память=%d, режим=%s",
        settings.chat_model,
        settings.image_model,
        settings.memory_max_messages,
        prompts.default_mode,
    )

    return Dispatcher(
        settings=settings,
        prompts=prompts,
        memory=memory,
        openai_service=openai_service,
        image_service=image_service,
    )


async def main() -> None:
    try:
        settings = get_settings()
    except RuntimeError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    bot = create_bot(settings)
    dp = create_dispatcher(settings)
    register_handlers(dp)

    logger.info("Запуск polling (ProxyAPI: %s)", settings.openai_base_url)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
