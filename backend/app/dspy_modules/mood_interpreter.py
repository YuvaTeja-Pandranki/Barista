"""DSPy mood interpreter (Gemini or keyword fallback). Not used by main pipeline; mood_agent used instead."""

from __future__ import annotations

import json
import logging

import dspy

from app.dspy_modules.dspy_config import is_lm_available

logger = logging.getLogger(__name__)

SUPPORTED_MOODS = [
    "happy", "relaxed", "stressed", "tired", "excited",
    "calm", "focused", "sleepy", "energetic", "anxious",
    "bored", "motivated", "sad", "joyful", "curious",
    "content", "restless", "peaceful", "creative", "hungry",
]

_MOOD_LIST_STR = ", ".join(SUPPORTED_MOODS)


class MoodInterpretation(dspy.Signature):
    mood_text: str = dspy.InputField(desc="User's free-text mood description")

    mood_json: str = dspy.OutputField(
        desc=(
            "JSON object with exactly two keys: "
            f'"mood" (one of: {_MOOD_LIST_STR}), '
            '"energy" (low|medium|high)'
        ),
    )


class MoodInterpreter(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.generate = dspy.ChainOfThought(MoodInterpretation)

    def forward(self, mood_text: str) -> dict:
        if is_lm_available():
            try:
                result = self.generate(mood_text=mood_text)
                parsed = json.loads(result.mood_json)

                if parsed.get("mood") not in SUPPORTED_MOODS:
                    parsed["mood"] = self._closest_mood(parsed.get("mood", ""))
                if parsed.get("energy") not in ("low", "medium", "high"):
                    parsed["energy"] = "medium"

                logger.info("Gemini mood interpretation: %s", parsed)
                return parsed
            except Exception:
                logger.warning(
                    "LM mood interpretation failed; using keyword fallback",
                    exc_info=True,
                )

        return self._keyword_fallback(mood_text)

    @staticmethod
    def _closest_mood(raw: str) -> str:
        raw_lower = (raw or "").lower().strip()
        for m in SUPPORTED_MOODS:
            if m in raw_lower or raw_lower in m:
                return m
        return "calm"

    @staticmethod
    def _keyword_fallback(mood_text: str) -> dict:
        text = mood_text.lower()

        keyword_map: dict[str, tuple[str, str]] = {
            "burned out": ("tired", "low"),
            "exhausted": ("tired", "low"),
            "sleepy": ("sleepy", "low"),
            "tired": ("tired", "low"),
            "happy": ("happy", "high"),
            "excited": ("excited", "high"),
            "joyful": ("joyful", "high"),
            "great": ("happy", "high"),
            "energetic": ("energetic", "high"),
            "workout": ("energetic", "high"),
            "motivated": ("motivated", "high"),
            "stressed": ("stressed", "medium"),
            "anxious": ("anxious", "medium"),
            "overwhelmed": ("stressed", "medium"),
            "restless": ("restless", "medium"),
            "bored": ("bored", "low"),
            "sad": ("sad", "low"),
            "cozy": ("relaxed", "low"),
            "relaxed": ("relaxed", "low"),
            "calm": ("calm", "low"),
            "peaceful": ("peaceful", "low"),
            "focused": ("focused", "medium"),
            "curious": ("curious", "medium"),
            "creative": ("creative", "medium"),
            "content": ("content", "medium"),
            "hungry": ("hungry", "medium"),
        }

        for keyword, (mood, energy) in keyword_map.items():
            if keyword in text:
                return {"mood": mood, "energy": energy}

        return {"mood": "calm", "energy": "medium"}


mood_interpreter = MoodInterpreter()
