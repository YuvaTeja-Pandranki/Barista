"""POST /recommend-drink: run pipeline, return one drink."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.exceptions import (
    CoffeeProfileUnavailableError,
    MoodInterpretationUnavailableError,
    RealtimeDataUnavailableError,
    WeatherUnavailableError,
)
from app.graph.state import RecommendationState
from app.graph.workflow import recommendation_workflow
from app.schemas.request_models import DrinkRecommendationRequest
from app.schemas.response_models import DrinkRecommendationResponse
from app.services.image_service import generate_drink_image

router = APIRouter(tags=["Recommendations"])


@router.post(
    "/recommend-drink",
    response_model=DrinkRecommendationResponse,
    summary="Get a personalised drink recommendation",
    description=(
        "Accepts a mood description and location, then returns a single "
        "Starbucks drink recommendation tailored to the user's current "
        "state and environment.  Weather and time of day are derived "
        "automatically from the location. Requires real-time weather and "
        "AI services; no mock or fallback data."
    ),
)
async def recommend_drink(
    payload: DrinkRecommendationRequest,
) -> DrinkRecommendationResponse:
    initial_state: RecommendationState = {
        "mood_text": payload.mood_text,
        "location": payload.location,
        "mood_profile": None,
        "environment_context": None,
        "coffee_profile": None,
        "drink_recommendation": None,
    }

    try:
        final_state = await recommendation_workflow.ainvoke(initial_state)
    except (WeatherUnavailableError, MoodInterpretationUnavailableError, CoffeeProfileUnavailableError, RealtimeDataUnavailableError) as e:
        raise HTTPException(status_code=503, detail=e.message) from e
    except ValueError as e:
        if "GEMINI_API_KEY" in str(e) or "API key" in str(e).lower():
            raise HTTPException(status_code=503, detail=str(e)) from e
        raise

    rec = final_state["drink_recommendation"]
    rec["image_url"] = generate_drink_image(rec["image_prompt"])

    return DrinkRecommendationResponse(**rec)
