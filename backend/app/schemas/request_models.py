"""Request models."""

from pydantic import BaseModel, Field


class DrinkRecommendationRequest(BaseModel):
    mood_text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Free-text description of the user's current mood.",
        examples=["I'm feeling calm and a bit tired"],
    )
    location: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="City or region used to infer weather and local time automatically.",
        examples=["Seattle, WA"],
    )
