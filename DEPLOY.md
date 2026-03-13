# Deploy Starbucks Mood (free)

You can run the full app for free using **Render** (backend + frontend) or **Vercel** (frontend) + **Render** (backend). API keys stay in each platform’s environment variables; no keys in the repo.

---

## Easiest: Render Blueprint (one deploy)

1. Push this repo to GitHub (or GitLab/Bitbucket).
2. Go to [Render](https://render.com) → **New** → **Blueprint**.
3. Connect the repo. Render will read `render.yaml` and create two services (API + frontend).
4. In the dashboard, for **starbucks-mood-api** add env: `GEMINI_API_KEY`, `WEATHER_API_KEY`. For **starbucks-mood-frontend** add: `VITE_WEATHER_API_KEY`.  
   (`VITE_API_URL` is already set in the Blueprint to point at the backend.)
5. Click **Deploy**. When both are live, open the frontend service URL.

If your backend URL is not `https://starbucks-mood-api.onrender.com` (e.g. Render added a suffix), set **VITE_API_URL** on the frontend service to your backend’s URL and redeploy the frontend.

---

## Option A: All on Render (manual setup)

One account, two free services: Backend (Web Service) + Frontend (Static Site).

### 1. Backend (Web Service)

1. [Render](https://render.com) → **New** → **Web Service**.
2. Connect your repo; set **Root Directory** to `backend`.
3. **Build**: `pip install -r requirements.txt`
4. **Start**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **Instance type**: Free.
6. **Environment**: Add (from your local `.env` or dashboard):
   - `GEMINI_API_KEY`
   - `WEATHER_API_KEY`
   - Optional: `GEMINI_MODEL`, `GCP_PROJECT_ID`, `GCP_LOCATION`
7. Deploy. Note the URL (e.g. `https://starbucks-mood-xxxx.onrender.com`).

Free tier: service sleeps after ~15 min; first request after that may take ~1 min (cold start).

### 2. Frontend (Static Site)

1. **New** → **Static Site**.
2. Same repo; **Root Directory** = `frontend`.
3. **Build**: `npm install && npm run build`
4. **Publish directory**: `dist`
5. **Environment** (so the built app talks to your backend and weather):
   - `VITE_API_URL` = your backend URL, e.g. `https://starbucks-mood-xxxx.onrender.com`  
     (no trailing slash; the app will call `/recommend-drink`, `/menu`, `/feedback` on that origin)
   - `VITE_WEATHER_API_KEY` = your WeatherAPI key (for the in-ui weather preview)
6. Deploy. Open the given `.onrender.com` URL.

CORS is already set to allow any origin in the backend, so the static site can call the API from the browser.

---

## Option B: Vercel (frontend) + Render (backend)

Use Render only for the API; host the frontend on Vercel.

1. Deploy the **backend** on Render as in Option A (steps 1–7). Copy the backend URL.
2. [Vercel](https://vercel.com) → **Add New** → **Project** → import the same repo.
3. **Root Directory**: `frontend`
4. **Build**: `npm run build` (Vercel will run `npm install` if needed)
5. **Environment variables**:
   - `VITE_API_URL` = your Render backend URL (e.g. `https://starbucks-mood-xxxx.onrender.com`)
   - `VITE_WEATHER_API_KEY` = your WeatherAPI key
6. Deploy. Your app will be at a `*.vercel.app` URL.

---

## Env summary

| Variable              | Where        | Purpose                          |
|-----------------------|-------------|-----------------------------------|
| `GEMINI_API_KEY`      | Backend     | Gemini LLM (mood, coffee, GEPA)  |
| `WEATHER_API_KEY`     | Backend     | WeatherAPI (recommendation flow)  |
| `VITE_API_URL`        | Frontend    | Backend base URL (production)     |
| `VITE_WEATHER_API_KEY`| Frontend    | Weather preview in the UI         |

Do not commit `.env` or any file containing real API keys.

---

## Other free options

- **Railway**: Free credit per month; deploy backend (and optionally frontend) from repo; set `PORT` in start command.
- **Fly.io**: Free tier for small VMs; good if you want to run the backend in Docker (use `PORT` from env in `Dockerfile` CMD).
- **Vercel for backend**: Possible but not ideal; Python serverless has size/time limits and your stack (DSPy, LangGraph, Gemini) is easier to run as one long-lived process on Render/Railway/Fly.

For a single, no-cost setup, **Render for both backend and frontend (Option A)** is the simplest.
