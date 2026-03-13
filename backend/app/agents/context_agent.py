"""Context agent: location → live weather + time_of_day into state."""

from __future__ import annotations

from app.graph.state import RecommendationState
from app.services.weather_service import get_weather_context


def run(state: RecommendationState) -> RecommendationState:
    context = get_weather_context(state["location"])
    return {"environment_context": context}
