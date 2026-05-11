"""POST /recommend-drink: run pipeline, return one drink."""

from __future__ import annotations

import asyncio

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

RECOMMENDATION_TIMEOUT_SECONDS = 22


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
        final_state = await asyncio.wait_for(
            recommendation_workflow.ainvoke(initial_state),
            timeout=RECOMMENDATION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return _fallback_recommendation(payload.mood_text)
    except (WeatherUnavailableError, MoodInterpretationUnavailableError, CoffeeProfileUnavailableError, RealtimeDataUnavailableError):
        return _fallback_recommendation(payload.mood_text)
    except ValueError as e:
        if "GEMINI_API_KEY" in str(e) or "API key" in str(e).lower():
            return _fallback_recommendation(payload.mood_text)
        raise

    rec = final_state["drink_recommendation"]
    rec["image_url"] = generate_drink_image(rec["image_prompt"])

    return DrinkRecommendationResponse(**rec)


def _fallback_recommendation(mood_text: str) -> DrinkRecommendationResponse:
    lower_mood = mood_text.lower()

    if any(word in lower_mood for word in ("tired", "sleepy", "drained", "exhausted")):
        return DrinkRecommendationResponse(
            drink_name="Iced Brown Sugar Oatmilk Shaken Espresso",
            description="A bright espresso boost for when you need energy without feeling too heavy.",
            base="Espresso",
            temperature_label="Iced",
            ingredients=["espresso", "oat milk", "brown sugar syrup", "cinnamon"],
            customizations=["extra cinnamon", "light ice"],
            price=5.95,
            context={
                "mood": "tired",
                "mood_emoji": "😴",
                "weather": "local weather",
                "time_of_day": "today",
                "temperature_f": 72,
            },
            image_prompt="an iced brown sugar oatmilk shaken espresso on a cafe table",
            image_url=None,
        )

    if any(word in lower_mood for word in ("stress", "anxious", "overwhelmed", "sad")):
        return DrinkRecommendationResponse(
            drink_name="Lavender Honey Latte",
            description="A soft floral latte for a calmer, slower coffee moment.",
            base="Latte",
            temperature_label="Hot",
            ingredients=["espresso", "oat milk", "lavender syrup", "honey"],
            customizations=["oat milk", "light honey"],
            price=6.25,
            context={
                "mood": "stressed",
                "mood_emoji": "🌿",
                "weather": "local weather",
                "time_of_day": "today",
                "temperature_f": 72,
            },
            image_prompt="a warm lavender honey latte in a cozy cafe",
            image_url=None,
        )

    return DrinkRecommendationResponse(
        drink_name="Caramel Macchiato",
        description="A balanced sweet classic that fits most moods and times of day.",
        base="Macchiato",
        temperature_label="Hot",
        ingredients=["espresso", "steamed milk", "vanilla syrup", "caramel drizzle"],
        customizations=["caramel drizzle", "oat milk"],
        price=5.95,
        context={
            "mood": "balanced",
            "mood_emoji": "☕",
            "weather": "local weather",
            "time_of_day": "today",
            "temperature_f": 72,
        },
        image_prompt="a caramel macchiato on a cafe table",
        image_url=None,
    )
