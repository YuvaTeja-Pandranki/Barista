"""GET /weather: proxy to WeatherAPI, keeps the key server-side."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.exceptions import WeatherUnavailableError
from app.services.weather_service import get_weather_display

router = APIRouter(tags=["Weather"])


@router.get("/weather", summary="Proxy weather lookup")
async def get_weather(location: str = Query(..., min_length=1)) -> dict:
    try:
        return get_weather_display(location)
    except WeatherUnavailableError as e:
        raise HTTPException(status_code=503, detail=e.message) from e
