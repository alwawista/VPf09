"""Регистрация роутеров aiogram."""

from __future__ import annotations

from aiogram import Dispatcher

from handlers import chat, commands, image


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(commands.router)
    dp.include_router(image.router)
    dp.include_router(chat.router)
