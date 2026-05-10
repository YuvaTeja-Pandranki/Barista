# Visual Barista AI — Project Overview

A clear, step-by-step explanation of the entire project so you have full clarity on how it works.

---

## 1. What Is This Project?

**Visual Barista AI** is a **mood-based coffee recommendation system**. You tell it:
- **How you feel** (e.g. "I'm stressed after work")
- **Where you are** (e.g. "Seattle")

It then:
1. Interprets your mood
2. Fetches real-time weather and time for your location
3. Uses AI (DSPy + optional Gemini) to decide what kind of drink fits (hot/iced, flavor, energy)
4. Scores every drink on a Starbucks-style menu and picks the best match
5. Optionally **learns from your feedback** (thumbs up/down) so future recommendations improve (GEPA)

So: **input = mood + location → output = one recommended drink + optional feedback loop.**

---

## 2. Project Structure (Where Everything Lives)

```
Starbucks Mood/
├── backend/                    # Python FastAPI server
│   ├── app/
│   │   ├── main.py             # FastAPI app, CORS, routes
│   │   ├── config.py           # Settings, env vars
│   │   ├── graph/              # LangGraph workflow
│   │   │   ├── state.py        # Shared state (mood_text, mood_profile, coffee_profile, etc.)
│   │   │   └── workflow.py     # Pipeline: mood → context → coffee_profile → menu → price
│   │   ├── agents/             # Each step of the pipeline (LangGraph nodes)
│   │   │   ├── mood_agent.py
│   │   │   ├── context_agent.py
│   │   │   ├── coffee_profile_agent.py
│   │   │   ├── menu_blender_agent.py
│   │   │   └── price_guardrail_agent.py
│   │   ├── dspy_modules/       # DSPy + GEPA logic
│   │   │   ├── dspy_config.py
│   │   │   ├── coffee_profile_module.py   # Maps mood+weather+time → coffee profile
│   │   │   ├── price_guardrail.py         # Enforces minimum price
│   │   │   └── gepa_optimizer.py          # Learns from feedback (avoid/prefer rules)
│   │   ├── feedback/
│   │   │   └── feedback_store.py          # In-memory store of thumbs up/down
│   │   ├── routes/
│   │   │   ├── recommendation.py          # POST /recommend-drink
│   │   │   ├── feedback.py                # POST /feedback
│   │   │   └── debug.py                   # GET /feedback, GET /gepa (inspect state)
│   │   ├── schemas/           # Request/response models
│   │   ├── services/          # Weather, menu, mood helpers
│   │   └── llm/               # Gemini client for mood + GEPA reflection
│   ├── data/
│   │   └── starbucks_menu.json            # Drink list with tags, price, ingredients
│   ├── scripts/               # Evaluation and validation
│   │   ├── validate_system.py
│   │   ├── eval_suite.py
│   │   ├── distribution_shift_eval.py
│   │   └── cold_start_eval.py
│   └── .env                   # GEMINI_API_KEY, WEATHER_API_KEY
│
├── frontend/                   # Vue 3 + Vite
│   ├── src/
│   │   ├── App.vue             # Main UI: mood + location inputs, Generate, DrinkCard
│   │   ├── api.js              # Calls: getDrinkRecommendation, submitFeedback, fetchMenu
│   │   └── components/
│   │       ├── DrinkCard.vue   # Shows recommendation + Love It / Not for Me
│   │       └── GlassInput.vue
│   └── .env                    # VITE_WEATHER_API_KEY (optional, for weather preview)
│
├── docker-compose.yml          # Run backend + frontend in containers
└── PROJECT_OVERVIEW.md         # This file
```

---

## 3. User Journey (Step by Step)

1. **User opens the app** (e.g. http://localhost:5173).
2. **User types or speaks** their mood (e.g. "I feel tired after work") and location (e.g. "Seattle").
3. **Optional:** The frontend can show a weather preview for that location (uses WeatherAPI from the browser if `VITE_WEATHER_API_KEY` is set).
4. **User clicks "Generate Drink".**
5. **Frontend** sends `POST /api/recommend-drink` with `{ mood_text, location }`.
6. **Backend** runs the full pipeline (see Section 4) and returns one drink with name, description, temperature, ingredients, price, context (mood, weather, time), and an image prompt/URL.
7. **User sees the drink card** and can click **"Love It"** or **"Not for Me"**.
8. **If "Not for Me":** Frontend sends feedback to the backend and then **automatically requests a new recommendation** (so the next drink is different).
9. **If "Love It" or "Not for Me":** Frontend sends `POST /api/feedback` with drink name, coffee profile (temperature, flavor), environment (weather), and thumbs_up/thumbs_down.
10. **Backend** stores the feedback and runs **GEPA** to update learned rules (e.g. "in rain, avoid iced drinks"). Future recommendations for similar weather/mood will use these rules.

So the loop is: **Recommend → User reacts → Feedback stored → GEPA updates rules → Next recommendation is influenced.**

---

## 4. The Recommendation Pipeline (Backend, Step by Step)

The pipeline is a **LangGraph** workflow: one graph, five nodes in a row. Each node reads and writes a **shared state** object.

**State** (simplified):

- **Input (you provide):** `mood_text`, `location`
- **Filled by pipeline:** `mood_profile`, `environment_context`, `coffee_profile`, `drink_recommendation`

**Graph:**

```
START → mood_agent → context_agent → coffee_profile_agent → menu_blender_agent → price_guardrail_agent → END
```

### Step 1: Mood Agent

- **Input:** `mood_text` (e.g. "I'm stressed after work").
- **What it does:** Turns free text into a **structured mood profile**.
  - If **Gemini is available:** Sends the text to Gemini, asks for JSON with `mood`, `energy_level`, `comfort_preference`; validates and maps to allowed values.
  - If **no Gemini or eval mode:** Uses a **keyword fallback** (e.g. "stressed" → stressed, medium, comfort).
- **Output:** `mood_profile` with fields like `primary_emotion`, `energy_level`, `warmth_preference`, `comfort_preference`, etc. (built by `mood_service.build_mood_profile`).

So after this step we know: **mood category, energy, comfort preference.**

---

### Step 2: Context Agent

- **Input:** `location` (e.g. "Seattle").
- **What it does:** Calls **WeatherAPI** (backend) to get:
  - Current weather text (e.g. "Light rain")
  - Temperature (F)
  - Local time at that location
  - Derives **time_of_day**: morning / afternoon / evening from the hour.
- **Output:** `environment_context` (weather, temperature_f, time_of_day, season, etc.).

So after this step we know: **weather and time of day** for the user’s place.

---

### Step 3: Coffee Profile Agent (DSPy)

- **Input:** `mood_profile`, `environment_context`.
- **What it does:** Produces a **coffee profile** that the menu blender will use:
  - **temperature:** hot / iced (and in logic, "frappuccino" as a blended option)
  - **flavor:** floral, fruity, earthy, sweet, bitter
  - **energy:** low, medium, high
  - **body:** light, medium, full

  Implementation:
  - If **DSPy is configured with an LLM (e.g. Gemini):** Uses a **ChainOfThought** module: mood + weather + time_of_day → JSON coffee profile.
  - If **no LLM:** Uses a **deterministic fallback** (rules like: rainy/cold → hot; sunny/hot → iced; mood maps to flavor/energy/body).

- **Output:** `coffee_profile` = `{ temperature, flavor, energy, body }`.

So after this step we have a **target profile** (e.g. "hot, earthy, medium energy, full body") that the next step will match against the menu.

---

### Step 4: Menu Blender Agent

- **Input:** `mood_profile`, `environment_context`, `coffee_profile`, and the **full menu** (`starbucks_menu.json`).
- **What it does:**
  1. **Scores every drink** (0–9) using:
     - Temperature match (+3), flavor match (+2), energy match (+2), weather fit (+1), time-of-day fit (+1). Frappuccinos get a partial score when hot/iced are both avoided (neutral option).
  2. **Sorts by score** (highest first).
  3. **GEPA layer:** Reads `gepa_optimizer.learned_preferences` (e.g. `("rain", "iced") → "avoid"`). For the **current weather** it:
     - **Avoid:** Removes drinks whose tags match avoided temperatures (e.g. no iced drinks in rain). If that would remove everything, the filter is skipped so we don’t return nothing.
     - **Preferred:** Moves preferred-temperature drinks to the top.
  4. **Picks one drink** from the top score tier (random among ties for variety).
  5. Builds the **recommendation object**: drink name, description, base type, temperature label (hot/iced/blended), ingredients, customizations, price, context (mood, weather, time), image prompt.

- **Output:** `drink_recommendation` (the full card data).

So after this step we have **one chosen drink** and the text/card data for the frontend.

---

### Step 5: Price Guardrail Agent (DSPy)

- **Input:** `drink_recommendation` (includes `price`).
- **What it does:** Enforces a **minimum price** (e.g. $3.00). If the recommendation (or anything tampered via prompt injection) has a price below that, it **clamps** it to the floor and can add a `guardrail_note`. Implemented as a DSPy-style constraint so the system satisfies “DSPy assertions for price floor”.
- **Output:** Same `drink_recommendation` with possibly corrected `price` and optional note.

After this, the pipeline is done. The **recommendation route** then adds an `image_url` (from `image_service`) and returns the response to the frontend.

---

## 5. GEPA — Learning From Feedback

**GEPA** = **G**rounded **E**valuation & **P**rompt **A**lignment. In this project it’s the **feedback learning layer** that adjusts behavior based on thumbs up/down.

- **When feedback is submitted** (`POST /feedback`):
  1. The payload (drink name, coffee profile, environment, thumbs_up/thumbs_down) is **stored** in `feedback_store` (in-memory list).
  2. **GEPA** runs `analyze_feedback(feedback_store.get_all())`:
     - It **clears** and rebuilds `learned_preferences` from **all** stored feedback.
     - For each record it gets `weather` and `temperature` (from coffee_profile, e.g. "iced" or "hot").
     - **Key** = `(weather, temperature)` (normalized, lowercased). **Value** = `"avoid"` (thumbs_down) or `"preferred"` (thumbs_up). Last feedback for a given key wins (because we clear and re-process all).
  3. If there are any learned preferences, GEPA can **reflect** (optional Gemini call or deterministic text) to produce a short explanation of why rules exist and how the logic should adapt.

- **When a recommendation is made** (inside Menu Blender):
  - The **same** `learned_preferences` are used: for the **current weather** we filter out “avoid” temperatures and boost “preferred” ones before picking the top drink.

So: **Feedback → stored → GEPA builds (weather, temp) → avoid/prefer → next recommendation uses these rules.** No prior feedback and no GEPA rules = cold start (menu scoring only).

---

## 6. DSPy in This Project

**DSPy** is used in two places:

1. **Coffee Profile Module** (`coffee_profile_module.py`)
   - **Signature:** mood, weather, time_of_day → coffee_profile (JSON string).
   - With an LLM: **ChainOfThought** to produce temperature, flavor, energy, body.
   - Without LLM: deterministic rules (weather → temp; mood → flavor/energy/body).

2. **Price Guardrail** (`price_guardrail.py`)
   - **Input:** drink name, price. **Output:** validated price (and flags).
   - Ensures price ≥ floor (e.g. $3.00); used after the menu blender so any tampering is corrected.

So DSPy handles **“vibe → coffee profile”** and **“price safety”**.

---

## 7. Data and Configuration

- **Menu:** `backend/data/starbucks_menu.json` — list of drinks, each with `drink_name`, `ingredients`, `price`, `tags` (e.g. hot, iced, sweet, chai, bold). Tags drive scoring and GEPA (temperature tags).
- **Backend .env:** `GEMINI_API_KEY`, `WEATHER_API_KEY` (WeatherAPI.com). If missing, mood uses keyword fallback, weather uses defaults, GEPA reflection uses deterministic text.
- **Frontend .env:** `VITE_WEATHER_API_KEY` (optional) for the location weather preview in the UI; recommendation itself uses the backend’s weather.

---

## 8. Frontend Summary

- **App.vue:** Form (mood, location), “Generate Drink” button, optional weather preview, list of mood chips, “Show Drinks” (menu modal). Calls `getDrinkRecommendation()` and passes the result to `DrinkCard`. Listens for `@disliked` from `DrinkCard` and calls `generate()` again to get a new drink.
- **DrinkCard.vue:** Shows the recommended drink (image, name, description, base, temperature, ingredients, customizations, price, “Why this blend?” context). **“Love It”** / **“Not for Me”** call `submitFeedback()` with the right payload; **“Not for Me”** also emits `disliked` so the app fetches another recommendation.
- **api.js:** Axios client with `baseURL: '/api'`; `getDrinkRecommendation`, `submitFeedback`, `fetchMenu`. Vite proxies `/api` to the backend (e.g. port 8000).

---

## 9. How to Run

- **Backend:** From `backend/`, run `uvicorn app.main:app --host 0.0.0.0 --port 8000` (or `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`).
- **Frontend:** From `frontend/`, run `npm run dev` (serves on port 5173, proxies `/api` to 8000).
- **Docker:** `docker compose up --build` (see `DOCKER.md`).

Health check: `GET http://localhost:8000/health`.  
API docs: `http://localhost:8000/docs`.

---

## 10. Evaluation Scripts (Optional Clarity)

- **validate_system.py** — Quick backend checks (pipeline, GEPA, menu, etc.).
- **eval_suite.py** — Full dataset run: 200+ records, before/after GEPA accuracy, stress test, security (injection), architecture checks, report.
- **distribution_shift_eval.py** — Unseen weather/mood (fog, storm, heatwave; frustrated, sleepy, etc.); checks that the system still behaves when GEPA has no rules for those conditions.
- **cold_start_eval.py** — No GEPA, no feedback; 150 new users; diversity, drink distribution, failure analysis.

They all run with `EVAL_OFFLINE_MODE` so they don’t call Gemini (keyword + deterministic fallbacks).

---

## 11. One-Sentence Summary of Each Part

| Part | Role |
|------|------|
| **Mood Agent** | Free text → structured mood (Gemini or keywords). |
| **Context Agent** | Location → weather + time of day (WeatherAPI). |
| **Coffee Profile Agent** | Mood + weather + time → target profile (DSPy / deterministic). |
| **Menu Blender** | Score menu by profile + apply GEPA → pick one drink. |
| **Price Guardrail** | Enforce minimum price (DSPy). |
| **GEPA** | Thumbs up/down → (weather, temp) avoid/prefer rules → used in Menu Blender. |
| **Feedback Store** | In-memory list of all feedback records. |
| **Frontend** | Mood + location → recommend → show card → feedback → optional new recommendation. |

If you want more detail on any single step (e.g. exact scoring formula, or how GEPA avoids emptying the list), say which step and we can go deeper there.
