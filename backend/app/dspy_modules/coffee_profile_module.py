"""DSPy: mood + weather + time_of_day → coffee profile (LM or EVAL_OFFLINE_MODE fallback)."""

from __future__ import annotations

import json
import logging
import os

import dspy

from app.dspy_modules.dspy_config import is_lm_available
from app.exceptions import CoffeeProfileUnavailableError

logger = logging.getLogger(__name__)


class VibeToCoffeeProfile(dspy.Signature):
    mood: str = dspy.InputField(desc="Primary emotion / mood keyword")
    weather: str = dspy.InputField(desc="Current weather condition")
    time_of_day: str = dspy.InputField(desc="morning | afternoon | evening | night")
    coffee_profile: str = dspy.OutputField(
        desc=(
            'JSON object with keys: "temperature" (hot|iced), '
            '"flavor" (floral|fruity|earthy|sweet|bitter), '
            '"energy" (low|medium|high), '
            '"body" (light|medium|full)'
        ),
    )


class CoffeeProfileGenerator(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.generate = dspy.ChainOfThought(VibeToCoffeeProfile)

    def forward(
        self,
        mood: str,
        weather: str,
        time_of_day: str,
    ) -> str:
        if os.environ.get("EVAL_OFFLINE_MODE"):
            logger.debug("DSPy running in deterministic fallback (EVAL_OFFLINE_MODE)")
            return self._deterministic_fallback(mood, weather, time_of_day)

        if not is_lm_available():
            raise CoffeeProfileUnavailableError(
                "Coffee profile generation requires a configured LM. "
                "Set GEMINI_API_KEY (or OPENAI_API_KEY) in backend/.env."
            )

        try:
            result = self.generate(
                mood=mood,
                weather=weather,
                time_of_day=time_of_day,
            )
            logger.debug("Gemini coffee profile: %s", result.coffee_profile)
            return self._normalise_keys(result.coffee_profile)
        except Exception as e:
            logger.warning("LM coffee profile call failed: %s", e, exc_info=True)
            raise CoffeeProfileUnavailableError(
                "Coffee profile generation failed. The language model service may be temporarily unavailable."
            ) from e

    @staticmethod
    def _normalise_keys(raw: str) -> str:
        try:
            profile = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw
        if "richness" in profile and "body" not in profile:
            profile["body"] = profile.pop("richness")
        return json.dumps(profile)

    @staticmethod
    def _deterministic_fallback(
        mood: str,
        weather: str,
        time_of_day: str,
    ) -> str:
        mood_lower = mood.lower()
        weather_lower = weather.lower()
        tod_lower = time_of_day.lower()
        if any(w in weather_lower for w in ("sunny", "hot", "heatwave", "humid")):
            temperature = "iced"
        elif any(w in weather_lower for w in ("rainy", "snowy", "windy", "cold", "fog", "storm", "thunderstorm", "hail")):
            temperature = "hot"
        else:
            temperature = "hot" if tod_lower in ("morning", "evening", "night") else "iced"
        flavor_map: dict[str, str] = {
            "happy": "fruity", "relaxed": "floral", "stressed": "earthy",
            "tired": "sweet", "excited": "fruity", "calm": "floral",
            "focused": "earthy", "sleepy": "sweet", "energetic": "fruity",
            "anxious": "earthy", "bored": "sweet", "motivated": "bitter",
            "sad": "sweet", "joyful": "fruity", "curious": "floral",
            "content": "floral", "restless": "bitter", "peaceful": "floral",
            "creative": "fruity", "hungry": "sweet", "fatigued": "sweet",
            "frustrated": "earthy", "overwhelmed": "earthy", "adventurous": "fruity",
        }
        flavor = flavor_map.get(mood_lower, "sweet")
        energy_map: dict[str, str] = {
            "happy": "medium", "relaxed": "low", "stressed": "medium",
            "tired": "high", "excited": "high", "calm": "low",
            "focused": "medium", "sleepy": "low", "energetic": "high",
            "anxious": "medium", "bored": "low", "motivated": "high",
            "sad": "low", "joyful": "medium", "curious": "medium",
            "content": "low", "restless": "medium", "peaceful": "low",
            "creative": "medium", "hungry": "medium", "fatigued": "high",
            "frustrated": "medium", "overwhelmed": "low", "adventurous": "high",
        }
        energy = energy_map.get(mood_lower, "medium")
        body = "full" if tod_lower in ("morning", "night") else "medium"
        if mood_lower in ("calm", "relaxed", "peaceful", "sleepy"):
            body = "light"

        profile = {
            "temperature": temperature,
            "flavor": flavor,
            "energy": energy,
            "body": body,
        }
        logger.debug("Deterministic coffee profile: %s", profile)
        return json.dumps(profile)


coffee_profile_generator = CoffeeProfileGenerator()
