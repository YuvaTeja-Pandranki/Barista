"""
Visual Barista AI - Cold-Start Evaluation
==========================================
Verifies recommendation quality when NO GEPA rules exist and NO prior
user feedback is available (new users, cold start).
"""
from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import os as _os
_os.environ["EVAL_OFFLINE_MODE"] = "1"
import app.dspy_modules.dspy_config as _dc
_dc._lm_configured = False

from app.agents import mood_agent, coffee_profile_agent
from app.dspy_modules.gepa_optimizer import gepa_optimizer
from app.feedback.feedback_store import feedback_store
from app.services.menu_service import get_full_menu
from app.agents.menu_blender_agent import _score_drink, _apply_gepa_preferences
from app.dspy_modules.price_guardrail import PriceGuardrail

SEP = "=" * 70


def h(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


# ---------------------------------------------------------------------------
# 1. Cold-start dataset: 150 new users, no feedback, no GEPA
# ---------------------------------------------------------------------------

WEATHERS = [
    "clear", "rain", "cloudy", "partly cloudy", "hot", "snow",
    "fog", "windy", "humid", "overcast",
]
MOOD_TEXTS = [
    "feeling stressed after work", "exhausted and need caffeine", "ready to conquer the day",
    "in a great mood today", "feeling a bit down", "need to concentrate on work",
    "just chilling, feeling relaxed", "feeling nervous about things", "nothing to do, pretty bored",
    "feeling motivated", "peaceful and content", "super excited about today",
    "really sleepy today", "completely overwhelmed", "in a creative mood",
    "feeling curious", "up for an adventure", "so frustrated right now",
]
TIMES = ["morning", "afternoon", "evening", "night"]


def _expected_temp(weather: str, mood_text: str) -> str:
    """Derive expected temperature for mismatch detection."""
    w = weather.lower()
    cold = {"rain", "light rain", "cloudy", "partly cloudy", "overcast", "snow", "fog", "windy"}
    hot_w = {"clear", "hot", "sunny", "humid"}
    if w in cold:
        return "hot"
    if w in hot_w:
        return "iced"
    return "hot"  # default


def generate_cold_start_dataset(n: int = 150) -> list[dict[str, Any]]:
    """Generate n new-user records. No feedback, no GEPA."""
    random.seed(456)
    records = []
    for i in range(n):
        records.append({
            "mood_text": random.choice(MOOD_TEXTS),
            "weather": random.choice(WEATHERS),
            "time_of_day": random.choice(TIMES),
        })
    return records


# ---------------------------------------------------------------------------
# 2. Pipeline trace + run
# ---------------------------------------------------------------------------

@dataclass
class ColdStartTrace:
    record_id: int
    mood_text: str
    weather: str
    time_of_day: str
    dspy_profile: dict = field(default_factory=dict)
    candidate_list_size: int = 0
    top_5_drinks: list[str] = field(default_factory=list)  # names by score desc
    final_recommendation: str = ""
    final_drink_temp: str = ""
    final_score: int = 0
    price: float = 0.0
    expected_temp: str = ""
    temperature_mismatch: bool = False
    error: str = ""
    # For average candidate score: score of chosen drink
    chosen_drink_score: int = 0


def run_cold_start_record(rec: dict[str, Any], record_id: int) -> ColdStartTrace:
    trace = ColdStartTrace(
        record_id=record_id,
        mood_text=rec["mood_text"],
        weather=rec["weather"],
        time_of_day=rec["time_of_day"],
        expected_temp=_expected_temp(rec["weather"], rec["mood_text"]),
    )
    try:
        mood_state = mood_agent.run({
            "mood_text": rec["mood_text"], "location": "",
            "mood_profile": None, "environment_context": None,
            "coffee_profile": None, "drink_recommendation": None,
        })
        mood_profile = mood_state.get("mood_profile", {})

        env_ctx = {
            "weather": rec["weather"], "temperature_f": 55,
            "time_of_day": rec["time_of_day"], "season": "spring",
        }
        cp_state = coffee_profile_agent.run({
            "mood_text": rec["mood_text"], "location": "",
            "mood_profile": mood_profile, "environment_context": env_ctx,
            "coffee_profile": None, "drink_recommendation": None,
        })
        profile = cp_state.get("coffee_profile", {})
        trace.dspy_profile = profile

        menu = get_full_menu()
        scored = [(d, _score_drink(d, profile, rec["weather"], rec["time_of_day"])) for d in menu]
        scored.sort(key=lambda x: x[1], reverse=True)
        trace.candidate_list_size = len(scored)
        trace.top_5_drinks = [d["drink_name"] for d, _ in scored[:5]]

        weather_norm = rec["weather"].lower().strip()
        profile_temp = (profile.get("temperature", "") or "").lower().strip()
        filtered = _apply_gepa_preferences(scored, weather_norm, profile_temp)

        if not filtered:
            trace.error = "empty candidate list"
            return trace

        top_score = filtered[0][1]
        top_tier = [(d, s) for d, s in filtered if s == top_score]
        drink, score = random.choice(top_tier)
        trace.final_recommendation = drink["drink_name"]
        trace.chosen_drink_score = score
        trace.final_score = score
        tags = {t.lower() for t in drink.get("tags", [])}
        if "frappuccino" in tags:
            trace.final_drink_temp = "blended"
        elif "iced" in tags:
            trace.final_drink_temp = "iced"
        elif "hot" in tags:
            trace.final_drink_temp = "hot"
        else:
            trace.final_drink_temp = "unknown"

        enforced = PriceGuardrail().enforce({"drink_name": drink["drink_name"], "price": drink["price"]})
        trace.price = enforced["price"]
        trace.temperature_mismatch = trace.final_drink_temp != trace.expected_temp

    except Exception as e:
        trace.error = str(e)
    return trace


# ---------------------------------------------------------------------------
# 3. Compute metrics & detect problems
# ---------------------------------------------------------------------------

def compute_metrics(traces: list[ColdStartTrace]) -> dict[str, Any]:
    valid = [t for t in traces if not t.error]
    n = len(valid)
    if not n:
        return {
            "diversity_score": 0.0,
            "drink_frequency": {},
            "top_drink_pct": 0.0,
            "avg_candidate_score": 0.0,
            "empty_candidate_lists": len([t for t in traces if t.error == "empty candidate list"]),
            "profile_collapse_count": 0,
            "profile_collapse_ratio": 0.0,
            "same_drink_max_count": 0,
            "same_drink_max_name": "",
            "temperature_mismatch_count": 0,
        }

    drink_counts = Counter(t.final_recommendation for t in valid)
    unique_drinks = len(drink_counts)
    diversity_score = unique_drinks / min(n, 30)  # normalize by menu size ~30
    top_drink, top_count = drink_counts.most_common(1)[0]
    top_drink_pct = (top_count / n) * 100
    avg_candidate_score = sum(t.chosen_drink_score for t in valid) / n

    profile_strs = [json.dumps(t.dspy_profile, sort_keys=True) for t in valid]
    profile_counts = Counter(profile_strs)
    most_common_profile_count = profile_counts.most_common(1)[0][1]
    profile_collapse_ratio = most_common_profile_count / n

    return {
        "total_records": len(traces),
        "valid_runs": n,
        "errors": len(traces) - n,
        "diversity_score": round(diversity_score, 3),
        "unique_drinks": unique_drinks,
        "drink_frequency": dict(drink_counts),
        "top_drink_pct": round(top_drink_pct, 1),
        "top_drink_name": top_drink,
        "avg_candidate_score": round(avg_candidate_score, 2),
        "empty_candidate_lists": len([t for t in traces if "empty" in (t.error or "")]),
        "profile_collapse_count": most_common_profile_count,
        "profile_collapse_ratio": round(profile_collapse_ratio, 3),
        "same_drink_max_count": top_count,
        "same_drink_max_name": top_drink,
        "temperature_mismatch_count": sum(1 for t in valid if t.temperature_mismatch),
    }


# ---------------------------------------------------------------------------
# 4. Run pipeline and produce report
# ---------------------------------------------------------------------------

def run_eval(dataset: list[dict[str, Any]]) -> tuple[list[ColdStartTrace], dict[str, Any]]:
    traces = []
    for i, rec in enumerate(dataset):
        t = run_cold_start_record(rec, i)
        traces.append(t)
        if (i + 1) % 50 == 0:
            print(f"  ... {i + 1}/{len(dataset)} processed")
    metrics = compute_metrics(traces)
    return traces, metrics


def print_report(traces: list[ColdStartTrace], metrics: dict[str, Any]) -> None:
    h("COLD-START EVALUATION REPORT")

    print("\n  --- Dataset Statistics ---")
    print(f"  Total records:       {metrics['total_records']}")
    print(f"  Valid runs:          {metrics['valid_runs']}")
    print(f"  Pipeline errors:     {metrics['errors']}")
    weather_dist = Counter(t.weather for t in traces)
    time_dist = Counter(t.time_of_day for t in traces)
    print(f"  Weather distribution: {dict(weather_dist)}")
    print(f"  Time-of-day:          {dict(time_dist)}")

    print("\n  --- Drink Frequency Distribution ---")
    freq = metrics.get("drink_frequency", {})
    for drink, count in sorted(freq.items(), key=lambda x: -x[1]):
        pct = (count / metrics["valid_runs"]) * 100 if metrics["valid_runs"] else 0
        print(f"    {count:3d}  ({pct:5.1f}%)  {drink}")

    print("\n  --- Top Recommended Drinks ---")
    for drink, count in sorted(freq.items(), key=lambda x: -x[1])[:15]:
        print(f"    {count:3d}  {drink}")
    print(f"  Top drink: {metrics.get('top_drink_name', '')} at {metrics.get('top_drink_pct', 0):.1f}%")

    print("\n  --- Diversity Score ---")
    print(f"  Unique drinks:       {metrics.get('unique_drinks', 0)}")
    print(f"  Diversity score:     {metrics.get('diversity_score', 0):.3f}  (unique / menu size)")
    print(f"  Avg candidate score: {metrics.get('avg_candidate_score', 0):.2f}  (score of chosen drink)")

    print("\n  --- Failure Analysis ---")
    print(f"  Empty candidate lists:     {metrics.get('empty_candidate_lists', 0)}")
    print(f"  Profile collapse:          {metrics.get('profile_collapse_count', 0)} runs ({metrics.get('profile_collapse_ratio', 0):.1%} same profile)")
    print(f"  Same drink repeated max:   {metrics.get('same_drink_max_name', '')} ({metrics.get('same_drink_max_count', 0)}x)")
    print(f"  Temperature mismatch:      {metrics.get('temperature_mismatch_count', 0)}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    print(SEP)
    print("  Visual Barista AI - Cold-Start Evaluation")
    print("  (No GEPA rules, no prior user feedback)")
    print(SEP)

    gepa_optimizer.learned_preferences.clear()
    gepa_optimizer.reflections.clear()
    feedback_store.records.clear()
    import app.services.menu_service as _ms
    _ms._menu_cache = None

    h("1. Generating 150 New-User Records")
    dataset = generate_cold_start_dataset(150)
    print(f"  Generated {len(dataset)} records (mood_text, weather, time_of_day)")

    h("2. Running Full Pipeline (No GEPA)")
    traces, metrics = run_eval(dataset)
    print(f"  Valid: {metrics['valid_runs']}  Errors: {metrics['errors']}")
    print(f"  Diversity: {metrics['unique_drinks']} unique drinks  Top drink %: {metrics['top_drink_pct']}%")

    print_report(traces, metrics)
    print(f"\n{SEP}")


if __name__ == "__main__":
    main()
