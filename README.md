# Visual Barista — Mood-to-Menu Hyper-Personalization Engine

A full-stack AI application that recommends Starbucks drinks based on your mood and real-time weather context. Tell it how you feel and where you are — it does the rest.

---

## How It Works

```
User Input (mood + location)
        │
        ▼
  [Mood Agent]          ← DSPy interprets emotional state
        │
        ▼
  [Context Agent]       ← Fetches real-time weather + time of day
        │
        ▼
  [Coffee Profile Agent] ← Maps mood+context → drink profile (temp, intensity, flavor)
        │
        ▼
  [Menu Blender Agent]  ← Scores every Starbucks menu item against the profile
        │
        ▼
  [Price Guardrail Agent] ← Filters by budget constraints (DSPy)
        │
        ▼
  Recommended Drink + Explanation
        │
        ▼
  [Feedback Loop]       ← GEPA optimizer learns from thumbs up/down
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue.js 3 + Vite + CSS glassmorphism |
| Backend | FastAPI (Python 3.12) |
| AI Orchestration | LangGraph (multi-agent workflow) |
| AI Optimization | DSPy + GEPA (few-shot prompt optimization) |
| LLM | Google Gemini via `google-generativeai` |
| Weather | OpenWeatherMap API |
| Containerization | Docker + docker-compose |
| Frontend Deploy | Vercel |
| Backend Deploy | Render |

---

## Project Structure

```
Starbucks Mood/
├── frontend/                   # Vue.js + Vite app
│   ├── src/
│   │   ├── App.vue             # Root component
│   │   ├── api.js              # Axios API client
│   │   ├── styles.css          # Global styles (glassmorphism)
│   │   └── components/
│   │       ├── DrinkCard.vue   # Recommended drink display
│   │       └── GlassInput.vue  # Mood + location input form
│   ├── Dockerfile
│   └── nginx.conf
│
├── backend/                    # FastAPI server
│   ├── app/
│   │   ├── main.py             # App entry, CORS, router registration
│   │   ├── config.py           # Environment config (pydantic settings)
│   │   ├── agents/             # LangGraph agent nodes
│   │   │   ├── mood_agent.py
│   │   │   ├── context_agent.py
│   │   │   ├── coffee_profile_agent.py
│   │   │   ├── menu_blender_agent.py
│   │   │   └── price_guardrail_agent.py
│   │   ├── dspy_modules/       # DSPy signatures + GEPA optimizer
│   │   ├── graph/              # LangGraph workflow + state schema
│   │   ├── routes/             # FastAPI route handlers
│   │   ├── services/           # Weather, mood, menu, image services
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── feedback/           # Feedback store for GEPA loop
│   │   └── llm/                # Gemini client wrapper
│   ├── data/                   # Starbucks menu JSON
│   ├── scripts/                # Evaluation + testing scripts
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml          # Local full-stack run
├── render.yaml                 # Render backend deploy config
├── ARCHITECTURE.md             # Deep-dive architecture notes
├── DEPLOY.md                   # Deployment guide
└── DOCKER.md                   # Docker usage guide
```

---

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker (optional, for containerized run)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Create backend/.env
cp .env.example .env            # then fill in your keys

uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Create frontend/.env
echo "VITE_API_URL=http://localhost:8000" > .env

npm run dev
```

### Docker (full stack)

```bash
docker-compose up --build
```

Frontend → `http://localhost:5173`  
Backend → `http://localhost:8000`  
API docs → `http://localhost:8000/docs`

---

## Environment Variables

**`backend/.env`**

```env
GEMINI_API_KEY=your_gemini_api_key
WEATHER_API_KEY=your_openweathermap_api_key
```

**`frontend/.env`**

```env
VITE_API_URL=http://localhost:8000
```

Never commit `.env` files. See `.gitignore`.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/recommend` | Get a drink recommendation |
| `POST` | `/feedback` | Submit thumbs up/down feedback |
| `GET` | `/debug/graph` | View LangGraph workflow state |
| `GET` | `/health` | Health check |

**Request body for `/recommend`:**
```json
{
  "mood": "I'm exhausted after a long day",
  "location": "Seattle, WA",
  "budget": 7.00
}
```

---

## Deployment

See [DEPLOY.md](DEPLOY.md) for full instructions on deploying to Render (backend) and Vercel (frontend).

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed walkthrough of the LangGraph agent pipeline, DSPy module design, and the GEPA feedback optimization loop.
