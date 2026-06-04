"""Загрузка и работа с режимами из prompts.json."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PromptMode:
    mode_id: str
    name: str
    description: str
    system_prompt: str


class PromptManager:
    def __init__(self, prompts_path: Path) -> None:
        self._path = prompts_path
        self._default_mode = "assistant"
        self._modes: dict[str, PromptMode] = {}
        self.reload()

    def reload(self) -> None:
        with self._path.open(encoding="utf-8") as file:
            data = json.load(file)

        self._default_mode = data.get("default_prompt", "assistant")
        raw_prompts = data.get("prompts", {})
        modes: dict[str, PromptMode] = {}

        for mode_id, item in raw_prompts.items():
            if not isinstance(item, dict):
                continue
            modes[mode_id] = PromptMode(
                mode_id=mode_id,
                name=str(item.get("name", mode_id)),
                description=str(item.get("description", "")),
                system_prompt=str(item.get("system_prompt", "")),
            )

        if not modes:
            raise ValueError(f"В {self._path} нет ни одного режима в prompts")
        if self._default_mode not in modes:
            self._default_mode = next(iter(modes))

        self._modes = modes

    @property
    def default_mode(self) -> str:
        return self._default_mode

    def list_modes(self) -> list[PromptMode]:
        return list(self._modes.values())

    def get_mode(self, mode_id: str) -> PromptMode | None:
        return self._modes.get(mode_id)

    def get_system_prompt(self, mode_id: str) -> str:
        mode = self._modes.get(mode_id) or self._modes[self._default_mode]
        return mode.system_prompt

    def format_modes_list(self, current_mode_id: str) -> str:
        lines = ["<b>Доступные режимы:</b>\n"]
        for mode in self.list_modes():
            marker = " ✅" if mode.mode_id == current_mode_id else ""
            lines.append(
                f"• <b>{mode.name}</b>{marker}\n"
                f"  <code>{mode.mode_id}</code> — {mode.description}"
            )
        lines.append("\nВыберите режим кнопкой ниже или командой:\n<code>/mode developer</code>")
        return "\n".join(lines)
