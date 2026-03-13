"""Validation and debug snapshot for pipeline state."""

from __future__ import annotations

from typing import Any

REQUIRED_PROFILE_KEYS: list[str] = ["temperature", "flavor", "energy", "body"]


def validate_coffee_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "valid": all(k in profile for k in REQUIRED_PROFILE_KEYS),
        "missing_keys": [k for k in REQUIRED_PROFILE_KEYS if k not in profile],
    }


def debug_state_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "mood_profile": state.get("mood_profile"),
        "environment_context": state.get("environment_context"),
        "coffee_profile": state.get("coffee_profile"),
        "drink_recommendation": state.get("drink_recommendation"),
    }
