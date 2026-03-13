"""Response models."""

from pydantic import BaseModel, Field


class ContextSummary(BaseModel):
    mood: str = Field(..., description="Interpreted mood category")
    mood_emoji: str = Field(..., description="Emoji representing the mood")
    weather: str = Field(..., description="Current weather condition")
    time_of_day: str = Field(..., description="Time of day bucket")
    temperature_f: int = Field(..., description="Temperature in Fahrenheit")


class DrinkRecommendationResponse(BaseModel):
    drink_name: str = Field(
        ..., description="Display name of the recommended drink."
    )
    description: str = Field(
        ..., description="Short blurb explaining why this drink fits the user."
    )
    base: str = Field(
        ..., description="Base drink type (e.g. Latte, Cappuccino, Frappuccino)."
    )
    temperature_label: str = Field(
        ..., description="Hot or Iced."
    )
    ingredients: list[str] = Field(
        ..., description="Core ingredients."
    )
    customizations: list[str] = Field(
        default_factory=list,
        description="AI-suggested customization add-ons.",
    )
    price: float = Field(
        ..., ge=0, description="Price in USD."
    )
    context: ContextSummary = Field(
        ..., description="Sensory context that drove this recommendation."
    )
    image_prompt: str = Field(
        ..., description="Prompt for image generation."
    )
    image_url: str | None = Field(
        default=None, description="Base64 data URI of AI-generated image."
    )
