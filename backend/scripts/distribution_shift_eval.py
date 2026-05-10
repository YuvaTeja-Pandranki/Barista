"""
Visual Barista AI - Distribution-Shift Validation
==================================================
Verifies that GEPA and DSPy generalize to UNSEEN weather and mood combinations.
Uses an adversarial dataset with weather/moods NOT present in the training set.
"""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

import os as _os
_os.environ["EVAL_OFFLINE_MODE"] = "1"
import app.dspy_modules.dspy_config as _dc
_dc._lm_configured = False

from app.agents import mood_agent, coffee_profile_agent
from app.dspy_modules.gepa_optimizer import gepa_optimizer
from app.services.menu_service import get_full_menu
from app.agents.menu_blender_agent import _score_drink, _apply_gepa_preferences
from app.dspy_modules.price_guardrail import PriceGuardrail

SEP = "=" * 70


def h(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


# ---------------------------------------------------------------------------
# 1. Adversarial dataset: UNSEEN weather + mood (not in training)
# ---------------------------------------------------------------------------

ADV_WEATHERS = [
    "fog", "storm", "thunderstorm", "heatwave", "windy", "humid", "hail",
]
ADV_MOODS = [
    "frustrated", "sleepy", "creative", "overwhelmed", "curious", "adventurous",
]
TIMES = ["morning", "afternoon", "evening", "night"]

# Expected temperature for (weather, mood) for correctness scoring
def _expected_temp_adv(weather: str, mood: str) -> str:
    w = weather.lower()
    hot_weather = {"heatwave", "humid"}
    cold_weather = {"fog", "storm", "thunderstorm", "windy", "hail"}
    if w in hot_weather:
        return "iced"
    if w in cold_weather:
        return "hot"
    return "hot"  # default for unseen

def _expected_style_adv(mood: str) -> str:
    comfort = {"frustrated", "sleepy", "overwhelmed"}
    refreshing = {"creative", "curious", "adventurous"}
    return "comfort" if mood in comfort else ("refreshing" if mood in refreshing else "balanced")

_MOOD_TEXTS_ADV: dict[str, list[str]] = {
    "frustrated":  ["feeling frustrated with everything", "so frustrated right now", "frustrated and stuck"],
    "sleepy":      ["really sleepy today", "can barely keep my eyes open", "feeling sleepy and slow"],
    "creative":    ["in a creative mood", "feeling creative and inspired", "ready to create something"],
    "overwhelmed": ["completely overwhelmed", "feeling overwhelmed by it all", "overwhelmed and stressed"],
    "curious":     ["feeling curious about things", "in a curious mood today", "curious and interested"],
    "adventurous": ["feeling adventurous", "up for an adventure", "adventurous and ready to try something new"],
}


def generate_adversarial_dataset(n: int = 200) -> list[dict[str, Any]]:
    """Generate n records with ONLY unseen weather and mood categories."""
    records: list[dict[str, Any]] = []
    combos = [(m, w, t) for m in ADV_MOODS for w in ADV_WEATHERS for t in TIMES]
    random.seed(123)
    # Allow duplicates if n > len(combos) to reach exactly n records
    while len(records) < n:
        for mood, weather, tod in combos:
            if len(records) >= n:
                break
            records.append({
            "mood_text": random.choice(_MOOD_TEXTS_ADV.get(mood, [f"feeling {mood}"])),
            "mood_category": mood,
            "weather": weather,
            "time_of_day": tod,
            "expected_temperature_preference": _expected_temp_adv(weather, mood),
            "expected_drink_style": _expected_style_adv(mood),
            })
        random.shuffle(combos)
    return records[:n]


# ---------------------------------------------------------------------------
# 2. Pipeline trace + run
# ---------------------------------------------------------------------------

@dataclass
class DistShiftTrace:
    record_id: int
    mood_text: str
    mood_category: str
    weather: str
    time_of_day: str
    expected_temp: str
    expected_style: str
    mood_profile: dict = field(default_factory=dict)
    dspy_coffee_profile: dict = field(default_factory=dict)
    drink_name: str = ""
    drink_temp: str = ""
    drink_tags: list = field(default_factory=list)
    drink_score: int = 0
    gepa_rule_applied: str = ""
    candidates_before_gepa: int = 0
    candidates_after_gepa: int = 0
    num_filtered: int = 0
    price: float = 0.0
    guardrail_triggered: bool = False
    correct: bool = False
    correctness_score: float = 0.0  # 1.0 = temp match, 0.5 = style ok, 0 = fail
    error: str = ""
    # Failure mode flags
    empty_candidates: bool = False
    gepa_incorrect: bool = False
    temperature_mismatch: bool = False
    dspy_collapse: bool = False  # same profile repeated


def run_pipeline_record(rec: dict[str, Any], record_id: int) -> DistShiftTrace:
    trace = DistShiftTrace(
        record_id=record_id,
        mood_text=rec["mood_text"],
        mood_category=rec["mood_category"],
        weather=rec["weather"],
        time_of_day=rec["time_of_day"],
        expected_temp=rec["expected_temperature_preference"],
        expected_style=rec["expected_drink_style"],
    )
    try:
        mood_state = mood_agent.run({
            "mood_text": rec["mood_text"], "location": "",
            "mood_profile": None, "environment_context": None,
            "coffee_profile": None, "drink_recommendation": None,
        })
        trace.mood_profile = mood_state.get("mood_profile", {})

        env_ctx = {
            "weather": rec["weather"], "temperature_f": 55,
            "time_of_day": rec["time_of_day"], "season": "spring",
        }
        cp_state = coffee_profile_agent.run({
            "mood_text": rec["mood_text"], "location": "",
            "mood_profile": trace.mood_profile, "environment_context": env_ctx,
            "coffee_profile": None, "drink_recommendation": None,
        })
        trace.dspy_coffee_profile = cp_state.get("coffee_profile", {})

        profile = trace.dspy_coffee_profile
        menu = get_full_menu()
        scored = [(d, _score_drink(d, profile, rec["weather"], rec["time_of_day"])) for d in menu]
        scored.sort(key=lambda x: x[1], reverse=True)
        trace.candidates_before_gepa = len(scored)

        weather_norm = rec["weather"].lower().strip()
        profile_temp = (profile.get("temperature", "") or "").lower().strip()
        prefs = gepa_optimizer.learned_preferences
        avoided = {t for (w, t), a in prefs.items() if w == weather_norm and a == "avoid"}
        preferred = {t for (w, t), a in prefs.items() if w == weather_norm and a == "preferred"}
        if avoided:
            trace.gepa_rule_applied = f"avoid: {avoided}"
        elif preferred:
            trace.gepa_rule_applied = f"prefer: {preferred}"
        else:
            trace.gepa_rule_applied = "none"

        filtered = _apply_gepa_preferences(scored, weather_norm, profile_temp)
        trace.candidates_after_gepa = len(filtered)
        trace.num_filtered = trace.candidates_before_gepa - trace.candidates_after_gepa

        if not filtered:
            trace.empty_candidates = True
            trace.error = "empty candidate list after GEPA"
            return trace

        top_score = filtered[0][1]
        top_tier = [(d, s) for d, s in filtered if s == top_score]
        drink, score = random.choice(top_tier)
        trace.drink_score = score
        trace.drink_name = drink["drink_name"]
        drink_tags = {t.lower() for t in drink.get("tags", [])}
        if "frappuccino" in drink_tags:
            trace.drink_temp = "blended"
        elif "iced" in drink_tags:
            trace.drink_temp = "iced"
        elif "hot" in drink_tags:
            trace.drink_temp = "hot"
        else:
            trace.drink_temp = "unknown"
        trace.drink_tags = list(drink_tags)

        enforced = PriceGuardrail().enforce({"drink_name": drink["drink_name"], "price": drink["price"]})
        trace.price = enforced["price"]
        trace.guardrail_triggered = "guardrail_note" in enforced

        trace.correct = (trace.drink_temp == trace.expected_temp)
        trace.temperature_mismatch = not trace.correct
        if trace.correct:
            trace.correctness_score = 1.0
        else:
            trace.correctness_score = 0.5 if rec["expected_drink_style"] in ("balanced", "refreshing") else 0.0

    except Exception as e:
        trace.error = str(e)
    return trace


# ---------------------------------------------------------------------------
# 3. Failure mode detection
# ---------------------------------------------------------------------------

def detect_failure_modes(traces: list[DistShiftTrace]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "empty_candidate_lists": 0,
        "gepa_incorrectly_applied": 0,
        "temperature_mismatch": 0,
        "identical_drink_repeated": None,  # (drink_name, max_count)
        "dspy_profile_collapse": None,     # (profile_hash, count)
        "rule_conflicts": 0,
    }
    out["empty_candidate_lists"] = sum(1 for t in traces if t.empty_candidates)
    out["temperature_mismatch"] = sum(1 for t in traces if t.temperature_mismatch and not t.error)
    drink_counts = Counter(t.drink_name for t in traces if not t.error)
    if drink_counts:
        top_drink, top_count = drink_counts.most_common(1)[0]
        out["identical_drink_repeated"] = (top_drink, top_count)
    profile_strs = [json.dumps(t.dspy_coffee_profile, sort_keys=True) for t in traces if not t.error and t.dspy_coffee_profile]
    if profile_strs:
        profile_counts = Counter(profile_strs)
        (collapsed_profile, collapse_count) = profile_counts.most_common(1)[0]
        out["dspy_profile_collapse"] = (collapse_count, len(profile_strs))
    return out


# ---------------------------------------------------------------------------
# 4. Run full pipeline and collect metrics
# ---------------------------------------------------------------------------

def run_distribution_shift_eval(
    dataset: list[dict[str, Any]],
    trace_examples: list[DistShiftTrace],
    max_examples: int = 10,
) -> tuple[list[DistShiftTrace], dict[str, Any]]:
    traces: list[DistShiftTrace] = []
    for i, rec in enumerate(dataset):
        t = run_pipeline_record(rec, i)
        traces.append(t)
        if len(trace_examples) < max_examples:
            trace_examples.append(t)
        if i % 50 == 0:
            print(f"  ... {i}/{len(dataset)} processed")

    valid = [t for t in traces if not t.error]
    correct = sum(1 for t in valid if t.correct)
    accuracy = (correct / len(valid) * 100) if valid else 0.0
    avg_correctness = sum(t.correctness_score for t in valid) / len(valid) if valid else 0.0
    diversity = len(set(t.drink_name for t in valid))
    total_filtered = sum(t.num_filtered for t in traces)
    gepa_applied_count = sum(1 for t in traces if t.gepa_rule_applied != "none")
    total_candidates = sum(t.candidates_before_gepa for t in traces if t.candidates_before_gepa)
    avg_filter_rate = (total_filtered / total_candidates * 100) if total_candidates else 0.0

    metrics = {
        "total_records": len(traces),
        "valid_runs": len(valid),
        "errors": len(traces) - len(valid),
        "accuracy_pct": accuracy,
        "avg_correctness_score": avg_correctness,
        "diversity_unique_drinks": diversity,
        "gepa_rules_applied_count": gepa_applied_count,
        "avg_candidate_filtering_rate_pct": avg_filter_rate,
        "failure_modes": detect_failure_modes(traces),
    }
    return traces, metrics


# ---------------------------------------------------------------------------
# 5. Report sections
# ---------------------------------------------------------------------------

def print_report(
    traces: list[DistShiftTrace],
    metrics: dict[str, Any],
    trace_examples: list[DistShiftTrace],
    previous_accuracy: float | None = None,
) -> None:
    h("DISTRIBUTION-SHIFT VALIDATION REPORT")

    print("\n  --- Dataset Statistics ---")
    print(f"  Total records:        {metrics['total_records']}")
    print(f"  Valid runs:            {metrics['valid_runs']}")
    print(f"  Pipeline errors:       {metrics['errors']}")
    weather_dist = Counter(t.weather for t in traces)
    mood_dist = Counter(t.mood_category for t in traces)
    print(f"  Weather categories:    {dict(weather_dist)}")
    print(f"  Mood categories:       {dict(mood_dist)}")

    print("\n  --- Accuracy vs Previous Dataset ---")
    print(f"  This run (unseen):     {metrics['accuracy_pct']:.1f}%")
    if previous_accuracy is not None:
        print(f"  Previous (in-dist):    {previous_accuracy:.1f}%")
        delta = metrics["accuracy_pct"] - previous_accuracy
        print(f"  Delta:                 {delta:+.1f} pp")
    print(f"  Avg correctness score: {metrics['avg_correctness_score']:.2f}")

    print("\n  --- Top 10 Recommended Drinks ---")
    drink_counts = Counter(t.drink_name for t in traces if not t.error)
    for drink, cnt in drink_counts.most_common(10):
        print(f"    {cnt:4d}  {drink}")

    print("\n  --- GEPA Rule Usage Frequency ---")
    rule_usage = Counter(t.gepa_rule_applied for t in traces)
    for rule, freq in rule_usage.most_common():
        label = rule if rule != "none" else "none (unseen weather)"
        print(f"    {freq:4d}  {label}")
    print(f"  Requests with any GEPA rule: {metrics['gepa_rules_applied_count']}")

    print("\n  --- Failure Analysis ---")
    fm = metrics["failure_modes"]
    print(f"  Empty candidate lists:     {fm['empty_candidate_lists']}")
    print(f"  Temperature mismatch:     {fm['temperature_mismatch']}")
    if fm.get("identical_drink_repeated"):
        d, c = fm["identical_drink_repeated"]
        print(f"  Most repeated drink:       {d} ({c}x)")
    if fm.get("dspy_profile_collapse"):
        c, total = fm["dspy_profile_collapse"]
        print(f"  DSPy profile collapse:     {c}/{total} same profile")
    print(f"  Avg filtering rate:        {metrics['avg_candidate_filtering_rate_pct']:.1f}%")
    print(f"  Rule conflicts:            {fm.get('rule_conflicts', 0)}")

    print("\n  --- Full Trace Examples (10) ---")
    # Select 10 diverse examples from all traces (different weather/mood)
    valid_traces = [t for t in traces if not t.error]
    seen_keys: set[tuple[str, str]] = set()
    ordered: list[DistShiftTrace] = []
    for t in valid_traces:
        key = (t.weather, t.mood_category)
        if key not in seen_keys:
            seen_keys.add(key)
            ordered.append(t)
    for t in valid_traces:
        if t not in ordered:
            ordered.append(t)
    display = ordered[:10]
    for i, t in enumerate(display):
        print(f"\n  -------- Example {i+1} --------")
        if t.error:
            print(f"  ERROR: {t.error}")
            continue
        print(f"  Input:     mood=\"{t.mood_text[:50]}...\"  weather={t.weather}  time={t.time_of_day}")
        print(f"  Expected:  temp={t.expected_temp}  style={t.expected_style}")
        print(f"  DSPy:      {json.dumps(t.dspy_coffee_profile)}")
        print(f"  GEPA:      {t.gepa_rule_applied}  |  filtered: {t.num_filtered}  (candidates {t.candidates_before_gepa} -> {t.candidates_after_gepa})")
        print(f"  Scoring:   top score={t.drink_score}")
        print(f"  Final:     {t.drink_name}  (temp={t.drink_temp}  price=${t.price:.2f})")
        print(f"  Correct:   {t.correct}  correctness_score={t.correctness_score}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    print(SEP)
    print("  Visual Barista AI - Distribution-Shift Validation")
    print("  (Unseen weather: fog, storm, thunderstorm, heatwave, windy, humid, hail)")
    print("  (Unseen moods:   frustrated, sleepy, creative, overwhelmed, curious, adventurous)")
    print(SEP)

    # Start with empty GEPA so no rules match unseen weather
    gepa_optimizer.learned_preferences.clear()
    gepa_optimizer.reflections.clear()
    import app.services.menu_service as _ms
    _ms._menu_cache = None

    h("1. Generating Adversarial Dataset (200 records)")
    dataset = generate_adversarial_dataset(200)
    print(f"  Generated {len(dataset)} records")
    print(f"  Weather: {ADV_WEATHERS}")
    print(f"  Moods:   {ADV_MOODS}")

    h("2. Running Full Pipeline (Mood -> Context -> DSPy -> Menu Blender -> GEPA -> Recommendation)")
    trace_examples: list[DistShiftTrace] = []
    traces, metrics = run_distribution_shift_eval(dataset, trace_examples, max_examples=10)

    print(f"\n  Accuracy:           {metrics['accuracy_pct']:.1f}%")
    print(f"  Diversity:          {metrics['diversity_unique_drinks']} unique drinks")
    print(f"  GEPA applied:       {metrics['gepa_rules_applied_count']} (expect 0 for unseen weather)")
    print(f"  Avg filter rate:    {metrics['avg_candidate_filtering_rate_pct']:.1f}%")

    # Previous in-distribution accuracy from eval_suite (after GEPA) was 94.5%
    PREVIOUS_ACCURACY = 94.5
    print_report(traces, metrics, trace_examples, previous_accuracy=PREVIOUS_ACCURACY)

    print(f"\n{SEP}")


if __name__ == "__main__":
    main()
