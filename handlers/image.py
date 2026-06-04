"""Команда /image — генерация картинок через gpt-image-2."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message

from memory import BRANCH_IMAGE, ChatMemory
from utils.image_service import ImageGenerationService

router = Router(name="image")
logger = logging.getLogger(__name__)


@router.message(Command("image"))
async def cmd_image(
    message: Message,
    command: CommandObject,
    memory: ChatMemory,
    image_service: ImageGenerationService,
) -> None:
    if message.chat is None:
        return

    chat_id = message.chat.id

    if not command.args or not command.args.strip():
        memory.set_branch(chat_id, BRANCH_IMAGE)
        await message.answer(
            "<b>Режим генерации изображений</b>\n\n"
            "Отправьте описание картинки текстом или одной командой:\n"
            "<code>/image закат над горами в стиле акварели</code>\n\n"
            "Выйти из режима: /chat"
        )
        return

    await _generate_and_send(message, image_service, command.args.strip())


async def generate_from_prompt(
    message: Message,
    image_service: ImageGenerationService,
    prompt: str,
) -> None:
    """Вызывается из ветки image при обычном текстовом сообщении."""
    await _generate_and_send(message, image_service, prompt)


async def _generate_and_send(
    message: Message,
    image_service: ImageGenerationService,
    prompt: str,
) -> None:
    if message.chat is None:
        return

    chat_id = message.chat.id
    status = await message.answer("Генерирую изображение… Это может занять до 2 минут.")
    await message.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)

    try:
        result = await image_service.generate(prompt)
    except RuntimeError as exc:
        logger.exception("Ошибка генерации изображения")
        await status.edit_text(str(exc))
        return
    except Exception:
        logger.exception("Неожиданная ошибка при генерации")
        await status.edit_text(
            "Не удалось сгенерировать изображение. Проверьте PROXY_API_KEY и IMAGE_MODEL."
        )
        return

    caption = f"<b>Промпт:</b> {prompt[:400]}"
    if len(prompt) > 400:
        caption += "…"

    photo = BufferedInputFile(result.image_bytes, filename="generated.png")
    await message.answer_photo(photo, caption=caption)
    await status.delete()

    if result.cost_footer:
        await message.answer(result.cost_footer)
