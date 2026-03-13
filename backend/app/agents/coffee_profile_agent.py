"""Coffee profile agent: mood + context → DSPy coffee_profile."""

from __future__ import annotations

import json
import logging

from app.dspy_modules.coffee_profile_module import coffee_profile_generator
from app.graph.state import RecommendationState

logger = logging.getLogger(__name__)


def run(state: RecommendationState) -> RecommendationState:
    mood_profile: dict = state["mood_profile"]  # type: ignore[assignment]
    env_context: dict = state["environment_context"]  # type: ignore[assignment]

    raw_profile: str = coffee_profile_generator(
        mood=mood_profile["primary_emotion"],
        weather=env_context["weather"],
        time_of_day=env_context["time_of_day"],
    )

    try:
        profile_dict = json.loads(raw_profile)
    except (json.JSONDecodeError, TypeError):
        logger.warning("DSPy returned non-JSON coffee profile; using raw string")
        profile_dict = {"raw": raw_profile}

    logger.info("Coffee profile resolved: %s", profile_dict)
    return {"coffee_profile": profile_dict}
