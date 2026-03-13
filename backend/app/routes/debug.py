"""Debug: test-pipeline, GET feedback, GET gepa state."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.graph.state import RecommendationState
from app.graph.workflow import recommendation_workflow
from app.utils.debug_tools import debug_state_snapshot, validate_coffee_profile
from app.feedback.feedback_store import feedback_store
from app.dspy_modules.gepa_optimizer import gepa_optimizer

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get(
    "/test-pipeline",
    summary="Run a canned request through the full pipeline and return diagnostics",
)
async def test_pipeline() -> dict[str, Any]:
    initial_state: RecommendationState = {
        "mood_text": "I feel stressed",
        "location": "Seattle",
        "mood_profile": None,
        "environment_context": None,
        "coffee_profile": None,
        "drink_recommendation": None,
    }

    final_state = await recommendation_workflow.ainvoke(initial_state)

    coffee_profile = final_state.get("coffee_profile") or {}

    return {
        "coffee_profile_validation": validate_coffee_profile(coffee_profile),
        "state_snapshot": debug_state_snapshot(final_state),
    }


@router.get("/feedback", summary="Inspect all stored feedback records")
async def get_feedback_records() -> dict[str, Any]:
    """Return every feedback record in the in-memory store."""
    records = feedback_store.get_all()
    thumbs_up   = [r for r in records if r.get("feedback") == "thumbs_up"]
    thumbs_down = [r for r in records if r.get("feedback") == "thumbs_down"]
    return {
        "total": len(records),
        "thumbs_up_count": len(thumbs_up),
        "thumbs_down_count": len(thumbs_down),
        "records": records,
    }


@router.get("/gepa", summary="Inspect current GEPA learned preferences and reflections")
async def get_gepa_state() -> dict[str, Any]:
    prefs = gepa_optimizer.learned_preferences
    serialised = {
        f"{w}|{t}": action
        for (w, t), action in prefs.items()
    }
    return {
        "total_preferences": len(prefs),
        "learned_preferences": serialised,
        "avoid_rules": [k for k, v in serialised.items() if v == "avoid"],
        "preferred_rules": [k for k, v in serialised.items() if v == "preferred"],
        "reflections_count": len(gepa_optimizer.reflections),
        "latest_reflection": gepa_optimizer.get_latest_reflection(),
        "all_reflections": gepa_optimizer.reflections,
    }
