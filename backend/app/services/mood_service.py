"""Build MoodProfile from mood category + energy + comfort."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class MoodProfile:
    primary_emotion: str
    energy_level: str
    warmth_preference: str
    flavour_tendency: str
    comfort_preference: str = "balanced"


_MOOD_DEFAULTS: dict[str, tuple[str, str]] = {
    "happy":     ("iced",    "fruity"),
    "relaxed":   ("hot",     "floral"),
    "stressed":  ("hot",     "earthy"),
    "tired":     ("hot",     "sweet"),
    "excited":   ("iced",    "fruity"),
    "calm":      ("hot",     "floral"),
    "focused":   ("hot",     "earthy"),
    "sleepy":    ("hot",     "sweet"),
    "energetic": ("iced",    "fruity"),
    "anxious":   ("hot",     "earthy"),
    "bored":     ("iced",    "sweet"),
    "motivated": ("iced",    "bitter"),
    "sad":       ("hot",     "sweet"),
    "joyful":    ("iced",    "fruity"),
    "curious":   ("neutral", "floral"),
    "content":   ("hot",     "floral"),
    "restless":  ("iced",    "bitter"),
    "peaceful":  ("hot",     "floral"),
    "creative":  ("neutral", "fruity"),
    "hungry":    ("hot",     "sweet"),
}


def build_mood_profile(
    mood_category: str,
    energy_level: str,
    comfort_preference: str = "balanced",
) -> dict[str, Any]:
    warmth, flavour = _MOOD_DEFAULTS.get(
        mood_category.lower(),
        ("hot", "floral"),
    )

    profile = MoodProfile(
        primary_emotion=mood_category.lower(),
        energy_level=energy_level,
        warmth_preference=warmth,
        flavour_tendency=flavour,
        comfort_preference=comfort_preference,
    )
    return asdict(profile)


def analyse_mood(mood_text: str) -> MoodProfile:
    text_lower = mood_text.lower()

    if any(w in text_lower for w in ("tired", "sleepy", "exhausted")):
        return MoodProfile("tired", "low", "hot", "sweet")
    if any(w in text_lower for w in ("happy", "excited", "great")):
        return MoodProfile("happy", "high", "iced", "fruity")
    if any(w in text_lower for w in ("stressed", "anxious", "overwhelmed")):
        return MoodProfile("stressed", "medium", "hot", "earthy")

    return MoodProfile("calm", "medium", "hot", "floral")
