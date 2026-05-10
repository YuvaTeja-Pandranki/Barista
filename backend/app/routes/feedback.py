"""POST /feedback: store thumbs up/down and run GEPA."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.dspy_modules.gepa_optimizer import gepa_optimizer
from app.feedback.feedback_store import feedback_store

router = APIRouter(tags=["Feedback"])


class FeedbackRequest(BaseModel):
    drink_name: str = Field(..., description="Name of the recommended drink.")
    coffee_profile: dict[str, Any] = Field(
        ..., description="The coffee profile that produced the recommendation."
    )
    environment: dict[str, Any] = Field(
        ..., description="Environment context at the time of the recommendation."
    )
    feedback: str = Field(
        ...,
        pattern=r"^(thumbs_up|thumbs_down)$",
        description="User sentiment: thumbs_up or thumbs_down.",
    )


@router.post(
    "/feedback",
    summary="Submit feedback on a drink recommendation",
    description=(
        "Records user feedback and runs the GEPA optimizer to update "
        "learned preference rules."
    ),
)
async def submit_feedback(payload: FeedbackRequest) -> dict[str, Any]:
    record = payload.model_dump()
    feedback_store.add_feedback(record)

    preferences = gepa_optimizer.analyze_feedback(feedback_store.get_all())

    serialisable_prefs = {
        f"{weather}|{temperature}": action
        for (weather, temperature), action in preferences.items()
    }

    return {
        "status": "recorded",
        "total_feedback": len(feedback_store.get_all()),
        "learned_preferences": serialisable_prefs,
        "latest_reflection": gepa_optimizer.get_latest_reflection(),
    }
