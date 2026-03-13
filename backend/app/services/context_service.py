"""EnvironmentContext dataclass; build_context is legacy (context_agent uses weather_service)."""

from dataclasses import dataclass


@dataclass
class EnvironmentContext:
    weather: str
    temperature_f: int
    time_of_day: str
    season: str


def build_context(location: str, time_of_day: str) -> EnvironmentContext:
    location_lower = location.lower()

    if "seattle" in location_lower:
        weather, temp = "rainy", 52
    elif "phoenix" in location_lower or "arizona" in location_lower:
        weather, temp = "sunny", 95
    elif "new york" in location_lower:
        weather, temp = "cloudy", 58
    elif "chicago" in location_lower:
        weather, temp = "windy", 45
    else:
        weather, temp = "partly cloudy", 65

    season_map = {"morning": "spring", "afternoon": "summer", "evening": "fall", "night": "winter"}
    season = season_map.get(time_of_day.lower(), "spring")

    return EnvironmentContext(
        weather=weather,
        temperature_f=temp,
        time_of_day=time_of_day.lower(),
        season=season,
    )
