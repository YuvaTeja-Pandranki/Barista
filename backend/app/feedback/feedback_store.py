"""In-memory feedback store (process lifetime)."""

from __future__ import annotations

from typing import Any


class FeedbackStore:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def add_feedback(self, record: dict[str, Any]) -> None:
        self.records.append(record)

    def get_all(self) -> list[dict[str, Any]]:
        return self.records


feedback_store = FeedbackStore()
