"""Память диалога: режим и история сообщений по chat_id."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ChatMessage = dict[str, str]

BRANCH_CHAT = "chat"
BRANCH_IMAGE = "image"


class ChatMemory:
    """Хранит режим и последние сообщения для каждого чата."""

    def __init__(self, storage_path: Path, default_mode: str, max_messages: int) -> None:
        self._path = storage_path
        self._default_mode = default_mode
        self._max_messages = max_messages
        self._data: dict[str, Any] = {"chats": {}}
        self._load()

    def get_mode(self, chat_id: int) -> str:
        return self._chat(chat_id).get("mode", self._default_mode)

    def set_mode(self, chat_id: int, mode_id: str) -> None:
        chat = self._chat(chat_id)
        chat["mode"] = mode_id
        self._save()

    def get_branch(self, chat_id: int) -> str:
        branch = self._chat(chat_id).get("branch", BRANCH_CHAT)
        return branch if branch in {BRANCH_CHAT, BRANCH_IMAGE} else BRANCH_CHAT

    def set_branch(self, chat_id: int, branch: str) -> None:
        if branch not in {BRANCH_CHAT, BRANCH_IMAGE}:
            branch = BRANCH_CHAT
        chat = self._chat(chat_id)
        chat["branch"] = branch
        self._save()

    def get_messages(self, chat_id: int) -> list[ChatMessage]:
        raw = self._chat(chat_id).get("messages", [])
        if not isinstance(raw, list):
            return []
        return [msg for msg in raw if self._is_valid_message(msg)]

    def add_exchange(self, chat_id: int, user_text: str, assistant_text: str) -> None:
        chat = self._chat(chat_id)
        messages: list[ChatMessage] = chat.setdefault("messages", [])
        messages.append({"role": "user", "content": user_text})
        messages.append({"role": "assistant", "content": assistant_text})
        chat["messages"] = messages[-self._max_messages :]
        self._save()

    def clear_history(self, chat_id: int) -> None:
        chat = self._chat(chat_id)
        chat["messages"] = []
        chat["branch"] = BRANCH_CHAT
        self._save()

    def build_context_messages(self, chat_id: int) -> list[ChatMessage]:
        """Последние N сообщений для отправки в OpenAI (без system)."""
        return self.get_messages(chat_id)[-self._max_messages :]

    def _chat(self, chat_id: int) -> dict[str, Any]:
        key = str(chat_id)
        chats = self._data.setdefault("chats", {})
        if key not in chats:
            chats[key] = {
                "mode": self._default_mode,
                "branch": BRANCH_CHAT,
                "messages": [],
            }
        return chats[key]

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open(encoding="utf-8") as file:
                loaded = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Не удалось загрузить память из %s: %s", self._path, exc)
            return
        if isinstance(loaded, dict) and isinstance(loaded.get("chats"), dict):
            self._data = loaded

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as file:
            json.dump(self._data, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _is_valid_message(message: Any) -> bool:
        return (
            isinstance(message, dict)
            and message.get("role") in {"user", "assistant"}
            and isinstance(message.get("content"), str)
        )
