"""Live weather + local time via WeatherAPI. Requires WEATHER_API_KEY."""

from __future__ import annotations

import logging
import os

import requests
from dotenv import load_dotenv

from app.exceptions import WeatherUnavailableError

load_dotenv()

logger = logging.getLogger(__name__)

WEATHER_URL = "http://api.weatherapi.com/v1/current.json"


def get_weather_display(location: str) -> dict:
    """Return display-friendly weather data for the frontend proxy endpoint."""
    key = os.getenv("WEATHER_API_KEY", "")
    if not key:
        raise WeatherUnavailableError(
            "Weather service is unavailable: WEATHER_API_KEY is not set."
        )
    try:
        resp = requests.get(WEATHER_URL, params={"key": key, "q": location}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise WeatherUnavailableError(
            "Weather service is temporarily unavailable."
        ) from e

    return {
        "condition": data["current"]["condition"]["text"],
        "temp_c": round(data["current"]["temp_c"]),
        "localtime": data["location"]["localtime"],
        "location_name": data["location"]["name"],
    }


def get_weather_context(location: str) -> dict:
    key = os.getenv("WEATHER_API_KEY", "")

    if not key:
        logger.error("WEATHER_API_KEY not set")
        raise WeatherUnavailableError(
            "Weather service is unavailable: WEATHER_API_KEY is not set. "
            "Add it to backend/.env to use real-time weather."
        )

    try:
        resp = requests.get(
            WEATHER_URL,
            params={"key": key, "q": location},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.warning("WeatherAPI request failed: %s", e, exc_info=True)
        raise WeatherUnavailableError(
            "Weather service is temporarily unavailable. Please try again later."
        ) from e

    weather = data["current"]["condition"]["text"]
    temp_f = data["current"]["temp_f"]
    local_time = data["location"]["localtime"]

    hour = int(local_time.split(" ")[1].split(":")[0])

    if hour < 12:
        time_of_day = "morning"
    elif hour < 18:
        time_of_day = "afternoon"
    else:
        time_of_day = "evening"

    month = _extract_month(local_time)
    season = _month_to_season(month)

    return {
        "weather": weather,
        "temperature_f": int(temp_f),
        "time_of_day": time_of_day,
        "season": season,
    }


def _extract_month(local_time: str) -> int:
    try:
        return int(local_time.split("-")[1])
    except (IndexError, ValueError):
        return 1


def _month_to_season(month: int) -> str:
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "fall"
    return "winter"
