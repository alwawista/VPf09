"""Команды бота: /start, /help, /mode, /reset."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from memory import BRANCH_CHAT, ChatMemory
from utils.prompts import PromptManager

router = Router(name="commands")


class ModeCallback(CallbackData, prefix="mode"):
    mode_id: str


def build_mode_keyboard(prompts: PromptManager, current_mode: str):
    builder = InlineKeyboardBuilder()
    for mode in prompts.list_modes():
        label = f"{'✓ ' if mode.mode_id == current_mode else ''}{mode.name}"
        builder.button(
            text=label,
            callback_data=ModeCallback(mode_id=mode.mode_id).pack(),
        )
    builder.adjust(1)
    return builder.as_markup()


@router.message(Command("start"))
async def cmd_start(message: Message, prompts: PromptManager, memory: ChatMemory) -> None:
    if message.chat is None:
        return
    mode = memory.get_mode(message.chat.id)
    current = prompts.get_mode(mode)
    mode_name = current.name if current else mode
    await message.answer(
        "Привет! Я AI-ассистент с памятью диалога и переключаемыми режимами.\n\n"
        f"Текущий режим: <b>{mode_name}</b>\n\n"
        "Команды:\n"
        "/mode — выбрать режим чата\n"
        "/image — генерация картинки (gpt-image-2)\n"
        "/reset — очистить историю\n"
        "/help — справка\n\n"
        "Просто напиши сообщение — я отвечу с учётом контекста."
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Справка</b>\n\n"
        "/start — приветствие\n"
        "/mode — список режимов и выбор\n"
        "/mode &lt;id&gt; — сразу переключить (например: /mode developer)\n"
        "/reset — очистить память диалога\n"
        "/image — режим генерации изображений\n"
        "/image &lt;промпт&gt; — сразу сгенерировать картинку\n"
        "/chat — выйти из режима изображений\n\n"
        "Режимы чата — в <code>prompts.json</code>."
    )


@router.message(Command("chat"))
async def cmd_chat(message: Message, memory: ChatMemory) -> None:
    if message.chat is None:
        return
    memory.set_branch(message.chat.id, BRANCH_CHAT)
    await message.answer("Режим чата. Пишите сообщения — отвечу с учётом контекста и выбранного /mode.")


@router.message(Command("reset"))
async def cmd_reset(message: Message, memory: ChatMemory) -> None:
    if message.chat is None:
        return
    memory.clear_history(message.chat.id)
    await message.answer("История диалога очищена. Можем начать с чистого листа.")


@router.message(Command("mode"))
async def cmd_mode(
    message: Message,
    command: CommandObject,
    prompts: PromptManager,
    memory: ChatMemory,
) -> None:
    if message.chat is None:
        return

    chat_id = message.chat.id
    current_mode = memory.get_mode(chat_id)

    if command.args:
        mode_id = command.args.strip().split()[0]
        selected = prompts.get_mode(mode_id)
        if selected is None:
            await message.answer(
                f"Режим <code>{mode_id}</code> не найден.\n\n"
                + prompts.format_modes_list(current_mode),
                reply_markup=build_mode_keyboard(prompts, current_mode),
            )
            return
        memory.set_mode(chat_id, mode_id)
        await message.answer(
            f"Режим переключён: <b>{selected.name}</b>\n{selected.description}",
            reply_markup=build_mode_keyboard(prompts, mode_id),
        )
        return

    await message.answer(
        prompts.format_modes_list(current_mode),
        reply_markup=build_mode_keyboard(prompts, current_mode),
    )


@router.callback_query(ModeCallback.filter())
async def on_mode_selected(
    query: CallbackQuery,
    callback_data: ModeCallback,
    prompts: PromptManager,
    memory: ChatMemory,
) -> None:
    if query.message is None or query.message.chat is None:
        await query.answer("Сообщение недоступно", show_alert=True)
        return

    selected = prompts.get_mode(callback_data.mode_id)
    if selected is None:
        await query.answer("Режим не найден", show_alert=True)
        return

    chat_id = query.message.chat.id
    memory.set_mode(chat_id, callback_data.mode_id)

    await query.message.edit_text(
        f"Режим: <b>{selected.name}</b>\n{selected.description}\n\n"
        + prompts.format_modes_list(callback_data.mode_id),
        reply_markup=build_mode_keyboard(prompts, callback_data.mode_id),
    )
    await query.answer(f"Выбран режим: {selected.name}")
