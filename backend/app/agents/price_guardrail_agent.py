"""Price guardrail agent: enforce minimum drink price."""

from __future__ import annotations

import logging

from app.dspy_modules.price_guardrail import PriceGuardrail
from app.graph.state import RecommendationState

logger = logging.getLogger(__name__)

_guardrail = PriceGuardrail()


def run(state: RecommendationState) -> RecommendationState:
    recommendation: dict | None = state.get("drink_recommendation")

    if recommendation:
        recommendation = _guardrail.enforce(recommendation)

        if recommendation.get("guardrail_note"):
            logger.warning("DSPy Assert: %s", recommendation["guardrail_note"])

    return {"drink_recommendation": recommendation}
