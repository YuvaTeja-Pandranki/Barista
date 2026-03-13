"""Shared state for the recommendation LangGraph workflow."""

from __future__ import annotations

from typing import TypedDict


class RecommendationState(TypedDict):
    mood_text: str
    location: str
    mood_profile: dict | None
    environment_context: dict | None
    coffee_profile: dict | None
    drink_recommendation: dict | None
