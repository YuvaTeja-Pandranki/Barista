"""GEPA: learn (weather, temp) → avoid/prefer from feedback; optional Gemini reflection."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class GEPAOptimizer:
    def __init__(self) -> None:
        self.learned_preferences: dict[tuple[str, str], str] = {}
        self.reflections: list[dict[str, Any]] = []

    def analyze_feedback(
        self, records: list[dict[str, Any]]
    ) -> dict[tuple[str, str], str]:
        self.learned_preferences.clear()

        for r in records:
            weather: str = r.get("environment", {}).get("weather", "").lower().strip()
            temperature: str = r.get("coffee_profile", {}).get("temperature", "").lower().strip()
            feedback: str = r.get("feedback", "")

            if not weather or not temperature:
                continue

            key = (weather, temperature)

            if feedback == "thumbs_down":
                self.learned_preferences[key] = "avoid"
            elif feedback == "thumbs_up":
                self.learned_preferences[key] = "preferred"

        if self.learned_preferences:
            self._reflect_on_patterns(records)

        return self.learned_preferences

    def _reflect_on_patterns(self, records: list[dict[str, Any]]) -> None:
        import os
        if os.environ.get("EVAL_OFFLINE_MODE"):
            self._deterministic_reflection()
            return
        try:
            from app.llm.gemini_client import get_gemini_client
            client, model_name = get_gemini_client()
        except Exception as e:
            logger.info("Gemini unavailable for GEPA reflection; skipping reflection: %s", e)
            return

        prefs_summary = "\n".join(
            f"  - {weather} weather + {temp} drinks -> {action}"
            for (weather, temp), action in self.learned_preferences.items()
        )

        thumbs_down = [r for r in records if r.get("feedback") == "thumbs_down"]
        failure_examples = ""
        for r in thumbs_down[:5]:
            env = r.get("environment", {})
            prof = r.get("coffee_profile", {})
            failure_examples += (
                f"  - Drink: {r.get('drink_name', '?')}, "
                f"Weather: {env.get('weather', '?')}, "
                f"Temperature: {prof.get('temperature', '?')}, "
                f"Flavor: {prof.get('flavor', '?')}\n"
            )

        prompt = f"""\
You are a recommendation engine optimizer analyzing user feedback patterns.

Learned preference rules:
{prefs_summary}

Recent thumbs-down examples:
{failure_examples}

Reflect on these patterns and answer in JSON:
{{
  "failure_analysis": "Why are users rejecting these recommendations?",
  "evolved_logic": "How should the recommendation logic change?",
  "ingredient_strategy": "What ingredient families should be prioritized or avoided?"
}}

Return ONLY valid JSON. No explanations outside the JSON."""

        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                raw = raw.rsplit("```", 1)[0].strip()

            reflection = json.loads(raw)
            self.reflections.append(reflection)
            logger.info("GEPA reflection: %s", json.dumps(reflection, indent=2))
        except Exception as e:
            logger.warning("Gemini GEPA reflection failed; skipping reflection: %s", e, exc_info=True)

    def _deterministic_reflection(self) -> None:
        for (weather, temp), action in self.learned_preferences.items():
            if action == "avoid":
                reflection = {
                    "failure_analysis": (
                        f"Users consistently reject {temp} drinks during "
                        f"{weather} weather. This suggests a mismatch between "
                        f"drink temperature and environmental comfort needs."
                    ),
                    "evolved_logic": (
                        f"During {weather} weather, prioritize comfort-based "
                        f"ingredients (warm spices, chocolate, honey) over "
                        f"{temp} options. Shift scoring to favor hot, "
                        f"soothing beverages."
                    ),
                    "ingredient_strategy": (
                        f"Avoid: {temp} drinks, cold brew, iced refreshers. "
                        f"Prioritize: warm lattes, chai, hot chocolate, "
                        f"steamed milk drinks with cinnamon or vanilla."
                    ),
                }
                self.reflections.append(reflection)
                logger.info("GEPA deterministic reflection: %s", reflection)

    def get_latest_reflection(self) -> dict[str, Any] | None:
        return self.reflections[-1] if self.reflections else None


gepa_optimizer = GEPAOptimizer()
