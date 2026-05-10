"""Enforce minimum drink price (clamp below floor, flag violation)."""

from __future__ import annotations

import logging
from typing import Any

import dspy

logger = logging.getLogger(__name__)

PRICE_FLOOR: float = 3.00


class PriceValidation(dspy.Signature):
    drink_name: str = dspy.InputField(desc="Name of the recommended drink")
    original_price: float = dspy.InputField(desc="Price from the recommendation")

    validated_price: float = dspy.OutputField(
        desc=f"Final price — must be >= ${PRICE_FLOOR:.2f}"
    )
    guardrail_triggered: bool = dspy.OutputField(
        desc="True if the price was below the floor and was corrected"
    )
    violation_reason: str = dspy.OutputField(
        desc="Explains why the guardrail fired, or empty string if no violation"
    )


class PriceGuardrail(dspy.Module):
    PRICE_FLOOR: float = PRICE_FLOOR

    def forward(self, drink_name: str, original_price: float) -> dspy.Prediction:
        constraint_met = original_price >= self.PRICE_FLOOR
        validated_price = original_price if constraint_met else self.PRICE_FLOOR

        if not constraint_met:
            reason = (
                f"Price ${original_price:.2f} violates minimum "
                f"${self.PRICE_FLOOR:.2f} for '{drink_name}'. "
                f"Possible prompt injection — clamped to floor."
            )
            logger.warning("DSPy price constraint failed: %s", reason)
        else:
            reason = ""

        assert validated_price >= self.PRICE_FLOOR, (
            f"CRITICAL: validated price ${validated_price:.2f} still below "
            f"floor ${self.PRICE_FLOOR:.2f} — guardrail logic error"
        )

        return dspy.Prediction(
            validated_price=validated_price,
            guardrail_triggered=not constraint_met,
            violation_reason=reason,
        )

    def enforce(self, recommendation: dict[str, Any]) -> dict[str, Any]:
        price: float = recommendation.get("price", 0)
        drink_name: str = recommendation.get("drink_name", "Unknown")

        result = self(drink_name=drink_name, original_price=price)

        recommendation["price"] = result.validated_price

        if result.guardrail_triggered:
            recommendation["guardrail_note"] = result.violation_reason

        return recommendation


def price_reward_fn(_args: dict, prediction: dspy.Prediction) -> float:
    return 1.0 if prediction.validated_price >= PRICE_FLOOR else 0.0


_guardrail = PriceGuardrail()

_r1 = _guardrail.enforce({"drink_name": "Test", "price": 1.50})
assert _r1["price"] == PRICE_FLOOR
assert "guardrail_note" in _r1

_r2 = _guardrail.enforce({"drink_name": "Test", "price": 5.00})
assert _r2["price"] == 5.00
assert "guardrail_note" not in _r2

_r3 = _guardrail.enforce({"drink_name": "Test", "price": 0.00})
assert _r3["price"] == PRICE_FLOOR
assert "guardrail_note" in _r3
