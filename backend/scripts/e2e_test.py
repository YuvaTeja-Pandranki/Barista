"""
E2E tests: hit the running backend (default http://localhost:8000).
Run: from repo root, start backend (uvicorn app.main:app --port 8000) then:
  cd backend && python scripts/e2e_test.py
Requires: GEMINI_API_KEY, WEATHER_API_KEY in backend/.env for full pipeline.
"""
from __future__ import annotations

import os
import sys
import time

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
TIMEOUT = 90


def run(name: str, ok: bool, msg: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}" + (f" — {msg}" if msg else ""))


def test_health() -> bool:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    ok = r.status_code == 200 and r.json().get("status") == "ok"
    run("GET /health", ok, r.text if not ok else "")
    return ok


def test_recommend_validation() -> bool:
    r = requests.post(
        f"{BASE_URL}/recommend-drink",
        json={"mood_text": "", "location": "Seattle"},
        timeout=5,
    )
    ok = r.status_code == 422
    run("POST /recommend-drink (invalid: empty mood) -> 422", ok, f"{r.status_code}" if not ok else "")
    return ok


def test_menu() -> bool:
    r = requests.get(f"{BASE_URL}/menu", timeout=5)
    data = r.json() if r.ok else None
    ok = r.status_code == 200 and isinstance(data, list) and len(data) > 0
    run("GET /menu", ok, r.text if not ok else f"{len(data) if data else 0} items")
    return ok


def test_recommend(mood: str, location: str) -> tuple[bool, dict | None]:
    r = requests.post(
        f"{BASE_URL}/recommend-drink",
        json={"mood_text": mood, "location": location},
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        run(f"POST /recommend-drink ({mood!r}, {location!r})", False, f"{r.status_code} {r.text[:200]}")
        return False, None
    data = r.json()
    required = ("drink_name", "description", "base", "price", "context", "ingredients")
    missing = [k for k in required if k not in data]
    ctx = data.get("context") or {}
    ctx_ok = isinstance(ctx, dict) and "mood" in ctx and "weather" in ctx
    ok = len(missing) == 0 and ctx_ok
    run(f"POST /recommend-drink ({mood!r}, {location!r})", ok, f"missing: {missing}" if missing else data.get("drink_name"))
    return ok, data


def test_feedback(rec: dict) -> bool:
    ctx = rec.get("context") or {}
    ingredients = rec.get("ingredients") or ["unknown"]
    payload = {
        "drink_name": rec["drink_name"],
        "coffee_profile": {
            "temperature": (rec.get("temperature_label") or "").lower(),
            "flavor": ingredients[0] if ingredients else "unknown",
        },
        "environment": {"weather": ctx.get("weather", "unknown")},
        "feedback": "thumbs_up",
    }
    r = requests.post(f"{BASE_URL}/feedback", json=payload, timeout=30)
    data = r.json() if r.ok else None
    ok = r.status_code == 200 and isinstance(data, dict) and data.get("status") == "recorded"
    run("POST /feedback (thumbs_up)", ok, r.text[:150] if not ok else "")
    return ok


def main() -> int:
    print(f"E2E base URL: {BASE_URL}\n")
    failed = 0

    if not test_health():
        failed += 1
    if not test_menu():
        failed += 1
    if not test_recommend_validation():
        failed += 1

    ok1, rec1 = test_recommend("I'm tired and need something calm after work", "Seattle, WA")
    if not ok1:
        failed += 1
    else:
        if not test_feedback(rec1):
            failed += 1

    ok2, _ = test_recommend("I feel energetic and happy, want a treat", "New York, NY")
    if not ok2:
        failed += 1

    print()
    if failed:
        print(f"Failed: {failed} test(s)")
        return 1
    print("All E2E tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
