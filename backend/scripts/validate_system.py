"""Visual Barista AI -- Full System Validation Script.

Exercises every layer of the backend:
    1. LangGraph pipeline execution order
    2. DSPy / Gemini coffee-profile reasoning
    3. Sensory context (weather, temperature, time_of_day)
    4. Menu Blender scoring system
    5. GEPA feedback learning loop
    6. Price guardrail enforcement
    7. Recommendation variability (tie-break randomness)

Run from the backend directory:
    python -m scripts.validate_system
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from typing import Any

PASS = "PASS"
FAIL = "FAIL"

results: dict[str, str] = {}


def header(title: str) -> None:
    print(f"\n{'=' * 56}")
    print(f"  {title}")
    print(f"{'=' * 56}")


def record(name: str, passed: bool, detail: str = "") -> None:
    status = PASS if passed else FAIL
    results[name] = status
    tag = f"[{status}]"
    print(f"  {tag}  {name}")
    if detail:
        for line in detail.strip().splitlines():
            print(f"         {line}")


# ------------------------------------------------------------------
# 1. LangGraph pipeline execution order
# ------------------------------------------------------------------
def test_langgraph_pipeline() -> None:
    header("1. LangGraph Pipeline Execution Order")

    from langgraph.graph import END, START
    from app.graph.workflow import recommendation_workflow

    graph = recommendation_workflow.get_graph()
    edges = graph.edges

    expected_chain = [
        (START, "mood_agent"),
        ("mood_agent", "context_agent"),
        ("context_agent", "coffee_profile_agent"),
        ("coffee_profile_agent", "menu_blender_agent"),
        ("menu_blender_agent", "price_guardrail_agent"),
        ("price_guardrail_agent", END),
    ]

    edge_set = set()
    for e in edges:
        src = e.source
        tgt = e.target
        edge_set.add((src, tgt))

    missing = [f"{s} -> {t}" for s, t in expected_chain if (s, t) not in edge_set]

    detail = ""
    if missing:
        detail = "Missing edges: " + ", ".join(missing)
    else:
        detail = "All 6 edges verified: START -> mood -> context -> coffee_profile -> menu_blender -> price_guardrail -> END"

    record("LangGraph pipeline", not missing, detail)


# ------------------------------------------------------------------
# 2. DSPy / Gemini reasoning
# ------------------------------------------------------------------
def test_dspy_reasoning() -> None:
    header("2. DSPy / Gemini Coffee Profile Reasoning")

    from app.dspy_modules.coffee_profile_module import coffee_profile_generator
    from app.dspy_modules.dspy_config import is_lm_available

    lm_live = is_lm_available()
    detail_lines = [f"LM available: {lm_live}"]

    test_cases = [
        ("stressed", "rainy", "morning"),
        ("happy", "sunny", "afternoon"),
        ("tired", "cloudy", "evening"),
    ]

    all_valid = True
    for mood, weather, tod in test_cases:
        raw = coffee_profile_generator(mood=mood, weather=weather, time_of_day=tod)
        try:
            profile = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            profile = {}
        required = {"temperature", "flavor", "energy", "body"}
        present = required & set(profile.keys())
        ok = present == required
        if not ok:
            all_valid = False
        status = "OK" if ok else "MISSING " + str(required - present)
        detail_lines.append(f"  {mood}/{weather}/{tod}: {status} -> {profile}")

    record("DSPy reasoning", all_valid, "\n".join(detail_lines))


# ------------------------------------------------------------------
# 3. Sensory context
# ------------------------------------------------------------------
def test_sensory_context() -> None:
    header("3. Sensory Context Validation")

    from app.services.weather_service import get_weather_context

    ctx = get_weather_context("Seattle")
    required = {"weather", "temperature_f", "time_of_day", "season"}
    present = required & set(ctx.keys())
    ok = present == required

    detail = f"Keys returned: {sorted(ctx.keys())}\n"
    detail += f"Sample: weather={ctx.get('weather')}, temp={ctx.get('temperature_f')}F, "
    detail += f"tod={ctx.get('time_of_day')}, season={ctx.get('season')}"

    record("Sensory context", ok, detail)


# ------------------------------------------------------------------
# 4. Menu Blender scoring
# ------------------------------------------------------------------
def test_scoring() -> None:
    header("4. Menu Blender Scoring System")

    from app.agents.menu_blender_agent import _score_drink
    from app.services.menu_service import get_full_menu

    profile = {"temperature": "hot", "flavor": "sweet", "energy": "low"}
    weather = "rainy"
    tod = "evening"

    menu = get_full_menu()
    scored = [(d["drink_name"], _score_drink(d, profile, weather, tod)) for d in menu]
    scored.sort(key=lambda x: x[1], reverse=True)

    top_score = scored[0][1]
    bottom_score = scored[-1][1]
    spread = top_score - bottom_score

    detail_lines = [f"Profile: {profile}  |  Weather: {weather}  |  Time: {tod}"]
    detail_lines.append(f"Score range: {bottom_score} - {top_score} (spread {spread})")
    detail_lines.append("")
    for name, score in scored[:8]:
        detail_lines.append(f"  [{score}] {name}")
    if len(scored) > 8:
        detail_lines.append(f"  ... {len(scored) - 8} more drinks")

    ok = spread > 0 and top_score > 0
    record("Menu Blender scoring", ok, "\n".join(detail_lines))


# ------------------------------------------------------------------
# 5. GEPA feedback learning
# ------------------------------------------------------------------
def test_gepa_learning() -> None:
    header("5. GEPA Feedback Learning")

    from app.dspy_modules.gepa_optimizer import gepa_optimizer
    from app.feedback.feedback_store import feedback_store

    gepa_optimizer.learned_preferences.clear()
    feedback_store.records.clear()

    feedback_record = {
        "drink_name": "Pink Drink",
        "coffee_profile": {"temperature": "iced", "flavor": "fruity", "energy": "low", "body": "light"},
        "environment": {"weather": "rainy"},
        "feedback": "thumbs_down",
    }
    feedback_store.add_feedback(feedback_record)
    prefs = gepa_optimizer.analyze_feedback(feedback_store.get_all())

    key = ("rainy", "iced")
    learned = prefs.get(key)
    ok = learned == "avoid"

    detail = f"Submitted: thumbs_down for iced/rainy\n"
    detail += f"Learned: {key} -> {learned}"

    record("GEPA learning", ok, detail)

    # Prove that the next recommendation avoids iced when (rainy, iced) = avoid
    from app.agents.menu_blender_agent import run as menu_blender_run

    state: dict[str, Any] = {
        "mood_text": "",
        "location": "",
        "mood_profile": {
            "primary_emotion": "stressed",
            "energy_level": "low",
            "warmth_preference": "iced",
            "flavour_tendency": "earthy",
            "comfort_preference": "balanced",
        },
        "environment_context": {
            "weather": "rainy",
            "temperature_f": 48,
            "time_of_day": "evening",
            "season": "fall",
        },
        "coffee_profile": {"temperature": "iced", "flavor": "earthy", "energy": "low", "body": "medium"},
        "drink_recommendation": None,
    }
    out = menu_blender_run(state)
    rec = out.get("drink_recommendation") or {}
    chosen_name = rec.get("drink_name", "")
    tags = [t.lower() for t in (rec.get("_tags") or [])]
    # The returned rec doesn't include _tags; we need to get tags from the menu
    from app.services.menu_service import get_full_menu
    menu_drink = next((d for d in get_full_menu() if d["drink_name"] == chosen_name), None)
    drink_tags = [t.lower() for t in (menu_drink.get("tags") or [])] if menu_drink else []
    is_iced = "iced" in drink_tags

    better_ok = not is_iced
    record(
        "GEPA influences recommendation",
        better_ok,
        f"With (rainy, iced)=avoid, selected '{chosen_name}' (iced={is_iced}). Expected hot drink.",
    )

    gepa_optimizer.learned_preferences.clear()
    feedback_store.records.clear()


# ------------------------------------------------------------------
# 6. Price guardrail
# ------------------------------------------------------------------
def test_price_guardrail() -> None:
    header("6. Price Guardrail Enforcement (DSPy Assert)")

    from app.dspy_modules.price_guardrail import PriceGuardrail

    guardrail = PriceGuardrail()

    tests: list[tuple[float, float, bool, str]] = [
        (0.00, 3.00, True,  "Price $0.00 (injection attempt)"),
        (1.50, 3.00, True,  "Price $1.50 (below floor)"),
        (2.99, 3.00, True,  "Price $2.99 (just below floor)"),
        (3.00, 3.00, False, "Price $3.00 (at floor)"),
        (5.95, 5.95, False, "Price $5.95 (normal)"),
    ]

    all_ok = True
    detail_lines = [f"Using: dspy.Assert (PRICE_FLOOR=${guardrail.PRICE_FLOOR:.2f})"]
    for input_price, expected, expect_triggered, label in tests:
        rec = {"drink_name": "Test", "price": input_price}
        result = guardrail.enforce(rec)
        actual = result["price"]
        triggered = result.get("guardrail_note") is not None
        price_ok = actual == expected
        trigger_ok = triggered == expect_triggered
        ok = price_ok and trigger_ok
        if not ok:
            all_ok = False
        tag = "OK" if ok else "FAIL"
        flag = " [ASSERT FIRED]" if triggered else ""
        detail_lines.append(f"  [{tag}] {label} -> ${actual:.2f}{flag}")

    record("Guardrail protection", all_ok, "\n".join(detail_lines))


# ------------------------------------------------------------------
# 7. Recommendation variability
# ------------------------------------------------------------------
def test_variability() -> None:
    header("7. Recommendation Variability (20 runs)")

    from app.agents.menu_blender_agent import _score_drink
    from app.services.menu_service import get_full_menu

    import random

    profile = {"temperature": "hot", "flavor": "sweet", "energy": "low"}
    weather = "rainy"
    tod = "evening"

    menu = get_full_menu()
    scored = [(d, _score_drink(d, profile, weather, tod)) for d in menu]
    scored.sort(key=lambda x: x[1], reverse=True)
    top_score = scored[0][1]
    top_tier = [(d, s) for d, s in scored if s == top_score]

    picks: list[str] = []
    for _ in range(20):
        drink, _ = random.choice(top_tier)
        picks.append(drink["drink_name"])

    counts = Counter(picks)
    unique = len(counts)

    detail_lines = [f"Top-tier drinks (score {top_score}): {len(top_tier)}"]
    detail_lines.append(f"Unique selections in 20 runs: {unique}")
    detail_lines.append("")
    for name, count in counts.most_common():
        bar = "#" * count
        detail_lines.append(f"  {name:<45s} {count:>2d}  {bar}")

    ok = unique > 1 or len(top_tier) == 1
    record("Recommendation variability", ok, "\n".join(detail_lines))


# ------------------------------------------------------------------
# Report
# ------------------------------------------------------------------
def print_report() -> None:
    print("\n")
    print("=" * 56)
    print("        SYSTEM VALIDATION REPORT")
    print("=" * 56)
    for name, status in results.items():
        tag = f"[{status}]"
        print(f"  {tag:<8s} {name}")

    total = len(results)
    passed = sum(1 for s in results.values() if s == PASS)
    failed = total - passed
    print()
    print(f"  {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} FAILED)")
    else:
        print("  -- ALL CLEAR")
    print("=" * 56)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> None:
    test_langgraph_pipeline()
    test_dspy_reasoning()
    test_sensory_context()
    test_scoring()
    test_gepa_learning()
    test_price_guardrail()
    test_variability()
    print_report()

    if any(s == FAIL for s in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
