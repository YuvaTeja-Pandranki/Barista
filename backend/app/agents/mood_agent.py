"""Mood agent: free-text mood → structured mood_profile via Gemini (or keyword fallback when EVAL_OFFLINE_MODE)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.graph.state import RecommendationState
from app.services.mood_service import build_mood_profile
from app.exceptions import MoodInterpretationUnavailableError

logger = logging.getLogger(__name__)

VALID_MOODS = [
    "happy", "relaxed", "stressed", "tired", "excited", "calm",
    "energetic", "focused", "anxious", "bored", "motivated", "sad",
]
VALID_ENERGY = ["low", "medium", "high"]
VALID_COMFORT = ["comfort", "balanced", "refreshing"]

_PROMPT_TEMPLATE = """\
User mood description:
"{mood_text}"

Extract the user's emotional state.

Return ONLY valid JSON with these fields:

{{
  "mood": one of {moods},
  "energy_level": one of ["low","medium","high"],
  "comfort_preference": one of ["comfort","balanced","refreshing"]
}}

Do not include explanations.\
"""


def _call_gemini(mood_text: str) -> dict[str, Any] | None:
    if os.environ.get("EVAL_OFFLINE_MODE"):
        return None
    try:
        from app.llm.gemini_client import get_gemini_client

        client, model_name = get_gemini_client()
        prompt = _PROMPT_TEMPLATE.format(
            mood_text=mood_text,
            moods=json.dumps(VALID_MOODS),
        )
        response = client.models.generate_content(model=model_name, contents=prompt)
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0].strip()

        parsed = json.loads(raw)

        if parsed.get("mood") not in VALID_MOODS:
            parsed["mood"] = _closest(parsed.get("mood", ""), VALID_MOODS, "calm")
        if parsed.get("energy_level") not in VALID_ENERGY:
            parsed["energy_level"] = "medium"
        if parsed.get("comfort_preference") not in VALID_COMFORT:
            parsed["comfort_preference"] = "balanced"

        logger.info("Gemini mood interpretation: %s", parsed)
        return parsed
    except Exception as e:
        logger.warning("Gemini mood interpretation failed: %s", e, exc_info=True)
        return None


def _closest(raw: str, options: list[str], default: str) -> str:
    raw_lower = (raw or "").lower().strip()
    for opt in options:
        if opt in raw_lower or raw_lower in opt:
            return opt
    return default


_KEYWORD_MAP: dict[str, tuple[str, str, str]] = {
    "burned out": ("tired",     "low",    "comfort"),
    "exhausted":  ("tired",     "low",    "comfort"),
    "sleepy":     ("tired",     "low",    "comfort"),
    "tired":      ("tired",     "low",    "comfort"),
    "happy":      ("happy",     "high",   "refreshing"),
    "good":       ("happy",     "medium", "balanced"),
    "great":      ("happy",     "high",   "refreshing"),
    "excited":    ("excited",   "high",   "refreshing"),
    "active":     ("energetic", "high",   "refreshing"),
    "energetic":  ("energetic", "high",   "refreshing"),
    "workout":    ("energetic", "high",   "refreshing"),
    "motivated":  ("motivated", "high",   "refreshing"),
    "stressed":   ("stressed",  "medium", "comfort"),
    "anxious":    ("anxious",   "medium", "comfort"),
    "overwhelmed":("stressed",  "low",    "comfort"),
    "bored":      ("bored",     "low",    "balanced"),
    "sad":        ("sad",       "low",    "comfort"),
    "relaxed":    ("relaxed",   "low",    "comfort"),
    "calm":       ("calm",      "low",    "comfort"),
    "focused":    ("focused",   "medium", "balanced"),
    "frustrated": ("stressed",  "medium", "comfort"),
    "creative":   ("focused",   "medium", "balanced"),
    "curious":    ("calm",      "medium", "balanced"),
    "adventurous":("excited",   "high",   "refreshing"),
}


def _keyword_fallback(mood_text: str) -> dict[str, Any]:
    text = mood_text.lower()
    for keyword, (mood, energy, comfort) in _KEYWORD_MAP.items():
        if keyword in text:
            return {"mood": mood, "energy_level": energy, "comfort_preference": comfort}
    return {"mood": "calm", "energy_level": "medium", "comfort_preference": "balanced"}


def run(state: RecommendationState) -> RecommendationState:
    mood_text = state["mood_text"]

    interpreted = _call_gemini(mood_text)
    if interpreted is None:
        if os.environ.get("EVAL_OFFLINE_MODE"):
            interpreted = _keyword_fallback(mood_text)
        else:
            raise MoodInterpretationUnavailableError(
                "Mood interpretation is unavailable. "
                "Ensure GEMINI_API_KEY is set in backend/.env and the service is reachable."
            )
    logger.info("Final mood interpretation for '%s': %s", mood_text, interpreted)

    profile = build_mood_profile(
        mood_category=interpreted["mood"],
        energy_level=interpreted["energy_level"],
        comfort_preference=interpreted["comfort_preference"],
    )

    return {"mood_profile": profile}
