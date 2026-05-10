"""Load and cache Starbucks menu from JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings

_menu_cache: list[dict[str, Any]] | None = None


def _load_menu() -> list[dict[str, Any]]:
    global _menu_cache
    if _menu_cache is None:
        menu_path = Path(settings.menu_data_path)
        if not menu_path.is_absolute():
            menu_path = Path(__file__).resolve().parents[2] / menu_path
        with menu_path.open(encoding="utf-8") as f:
            _menu_cache = json.load(f)
    return _menu_cache


def get_full_menu() -> list[dict[str, Any]]:
    return _load_menu()


def find_drink_by_name(name: str) -> dict[str, Any] | None:
    for item in _load_menu():
        if item["drink_name"].lower() == name.lower():
            return item
    return None


def filter_by_tags(tags: list[str]) -> list[dict[str, Any]]:
    tag_set = {t.lower() for t in tags}
    return [
        item
        for item in _load_menu()
        if tag_set & {t.lower() for t in item.get("tags", [])}
    ]
