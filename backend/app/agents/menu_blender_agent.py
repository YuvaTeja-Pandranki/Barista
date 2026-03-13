"""Menu blender: score menu by profile, apply GEPA, pick best drink."""

from __future__ import annotations

import logging
import random
from typing import Any

from app.dspy_modules.gepa_optimizer import gepa_optimizer
from app.graph.state import RecommendationState
from app.services.context_service import EnvironmentContext
from app.services.menu_service import get_full_menu
from app.services.mood_service import MoodProfile

logger = logging.getLogger(__name__)

_FLAVOR_TAGS: dict[str, set[str]] = {
    "floral":  {"floral", "lavender", "vanilla"},
    "fruity":  {"fruity", "refreshing", "berry", "tropical"},
    "earthy":  {"earthy", "chai", "matcha"},
    "sweet":   {"sweet", "caramel", "mocha", "chocolate"},
    "bitter":  {"bold", "espresso"},
}

_ENERGY_TAGS: dict[str, set[str]] = {
    "high":   {"bold", "espresso"},
    "medium": {"classic", "spiced"},
    "low":    {"refreshing"},
}

_COLD_WEATHER: set[str] = {
    "rain", "rainy", "drizzle", "light rain", "light drizzle",
    "snow", "snowy", "cold", "windy", "overcast", "cloudy",
    "partly cloudy", "mist", "fog",
}

_HOT_WEATHER: set[str] = {
    "sunny", "hot", "clear", "warm", "humid",
}

_MORNING_TAGS:   set[str] = {"bold", "espresso", "classic"}
_AFTERNOON_TAGS: set[str] = {"refreshing", "fruity", "iced"}
_EVENING_TAGS:   set[str] = {"sweet", "spiced", "chai", "chocolate"}


def _score_drink(
    drink: dict[str, Any],
    profile: dict[str, Any],
    weather: str,
    time_of_day: str,
) -> int:
    tags = {t.lower() for t in drink.get("tags", [])}
    score = 0
    desired_temp = profile.get("temperature", "")
    if desired_temp and desired_temp in tags:
        score += 3
    elif "frappuccino" in tags:
        score += 1
    flavor_family = _FLAVOR_TAGS.get(profile.get("flavor", ""), set())
    if tags & flavor_family:
        score += 2
    energy_family = _ENERGY_TAGS.get(profile.get("energy", ""), set())
    if tags & energy_family:
        score += 2
    weather_lower = weather.lower()
    if weather_lower in _COLD_WEATHER and "hot" in tags:
        score += 1
    elif weather_lower in _HOT_WEATHER and "iced" in tags:
        score += 1
    tod = time_of_day.lower()
    if tod == "morning" and (tags & _MORNING_TAGS):
        score += 1
    elif tod == "afternoon" and (tags & _AFTERNOON_TAGS):
        score += 1
    elif tod in ("evening", "night") and (tags & _EVENING_TAGS):
        score += 1

    return score


def _apply_gepa_preferences(
    candidates: list[tuple[dict[str, Any], int]],
    weather: str,
    temperature: str,
) -> list[tuple[dict[str, Any], int]]:
    preferences = gepa_optimizer.learned_preferences
    if not preferences:
        return candidates
    avoided_temps: set[str] = set()
    preferred_temps: set[str] = set()
    for (w, t), action in preferences.items():
        if w == weather:
            if action == "avoid":
                avoided_temps.add(t)
            elif action == "preferred":
                preferred_temps.add(t)
    result = candidates
    if avoided_temps:
        filtered = [
            (d, s) for d, s in result
            if not ({t.lower() for t in d.get("tags", [])} & avoided_temps)
        ]
        if filtered:
            logger.info(
                "GEPA: avoiding %s drinks in %s weather -- %d -> %d candidates",
                avoided_temps, weather, len(result), len(filtered),
            )
            result = filtered
        else:
            logger.info(
                "GEPA: avoid filter for %s|%s would empty the list; skipping",
                weather, avoided_temps,
            )
    if preferred_temps:
        preferred = [
            (d, s) for d, s in result
            if {t.lower() for t in d.get("tags", [])} & preferred_temps
        ]
        rest = [(d, s) for d, s in result if (d, s) not in preferred]
        if preferred:
            logger.info(
                "GEPA: prioritising %s drinks in %s weather -- %d boosted",
                preferred_temps, weather, len(preferred),
            )
            result = preferred + rest

    return result


def run(state: RecommendationState) -> RecommendationState:
    mood = MoodProfile(**state["mood_profile"])
    context = EnvironmentContext(**state["environment_context"])
    coffee_profile: dict[str, Any] | None = state.get("coffee_profile")

    profile = coffee_profile if coffee_profile and "flavor" in coffee_profile else {
        "temperature": mood.warmth_preference,
        "flavor": mood.flavour_tendency,
        "energy": mood.energy_level,
    }

    menu = get_full_menu()

    scored: list[tuple[dict[str, Any], int]] = [
        (drink, _score_drink(drink, profile, context.weather, context.time_of_day))
        for drink in menu
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    logger.info("Drink scores (profile=%s, weather=%s, time=%s):",
                profile, context.weather, context.time_of_day)
    for drink, score in scored:
        logger.info("  [%d] %s", score, drink["drink_name"])
    weather = context.weather.lower().strip() if context.weather else ""
    profile_temp = (profile.get("temperature", "") or "").lower().strip()
    if weather and profile_temp:
        scored = _apply_gepa_preferences(scored, weather, profile_temp)

    top_score = scored[0][1]
    top_tier = [(d, s) for d, s in scored if s == top_score]
    drink, _ = random.choice(top_tier)

    logger.info("Selected: %s (score %d, %d tied)", drink["drink_name"], top_score, len(top_tier))

    flavor_label = profile.get("flavor", mood.flavour_tendency)
    drink_tags = {t.lower() for t in drink.get("tags", [])}
    if "frappuccino" in drink_tags:
        temp_label = "blended"
    elif "iced" in drink_tags:
        temp_label = "iced"
    elif "hot" in drink_tags:
        temp_label = "hot"
    else:
        temp_label = profile.get("temperature", mood.warmth_preference)
    comfort = state.get("mood_profile", {}).get("comfort_preference", "balanced")

    description = (
        f"{_capitalize(comfort)} and {flavor_label} for your "
        f"{context.time_of_day} mood"
    )
    image_prompt = (
        f"a cinematic {drink['drink_name'].lower()} "
        f"in a cozy cafe on a {context.weather} {context.time_of_day}"
    )

    base = _infer_base(drink)
    customizations = _generate_customizations(profile, mood, context)

    return {
        "drink_recommendation": {
            "drink_name": drink["drink_name"],
            "description": description,
            "base": base,
            "temperature_label": _capitalize(temp_label),
            "ingredients": drink["ingredients"],
            "customizations": customizations,
            "price": drink["price"],
            "image_prompt": image_prompt,
            "context": {
                "mood": mood.primary_emotion,
                "mood_emoji": _MOOD_EMOJIS.get(mood.primary_emotion, "☕"),
                "weather": context.weather,
                "time_of_day": _capitalize(context.time_of_day),
                "temperature_f": context.temperature_f,
            },
        }
    }


def _capitalize(s: str) -> str:
    return s.capitalize() if s else s


_MOOD_EMOJIS: dict[str, str] = {
    "happy": "😊", "relaxed": "😌", "stressed": "😩", "tired": "😴",
    "excited": "🤩", "calm": "🧘", "focused": "🎯", "sleepy": "😪",
    "energetic": "⚡", "anxious": "😰", "bored": "😑", "motivated": "💪",
    "sad": "😢", "joyful": "🥳", "curious": "🤔", "content": "😊",
    "restless": "😤", "peaceful": "🕊️", "creative": "🎨", "hungry": "🍽️",
}

_BASE_KEYWORDS: dict[str, str] = {
    "latte": "Latte", "cappuccino": "Cappuccino", "frappuccino": "Frappuccino",
    "cold brew": "Cold Brew", "espresso": "Espresso", "americano": "Americano",
    "mocha": "Mocha", "macchiato": "Macchiato", "refresher": "Refresher",
    "tea": "Tea", "chocolate": "Hot Chocolate",
}


def _infer_base(drink: dict[str, Any]) -> str:
    name_lower = drink["drink_name"].lower()
    for kw, label in _BASE_KEYWORDS.items():
        if kw in name_lower:
            return label
    return "Specialty"


_CUSTOMIZATION_MAP: dict[str, list[str]] = {
    "floral":  ["lavender shot", "vanilla drizzle"],
    "fruity":  ["berry topping", "fruit syrup pump"],
    "earthy":  ["extra chai spice", "matcha boost"],
    "sweet":   ["caramel drizzle", "whipped cream"],
    "bitter":  ["extra espresso shot", "dark cocoa powder"],
}

_COMFORT_CUSTOMS: dict[str, list[str]] = {
    "comfort":     ["oat milk", "cinnamon dusting"],
    "refreshing":  ["light ice", "coconut milk"],
    "balanced":    ["non-fat milk"],
}


def _generate_customizations(
    profile: dict[str, Any],
    mood: MoodProfile,
    context: EnvironmentContext,
) -> list[str]:
    customs: list[str] = []

    flavor = profile.get("flavor", mood.flavour_tendency)
    customs.extend(_CUSTOMIZATION_MAP.get(flavor, [])[:2])

    comfort = getattr(mood, "comfort_preference", "balanced")
    customs.extend(_COMFORT_CUSTOMS.get(comfort, [])[:1])

    return customs
