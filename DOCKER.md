# Running Visual Barista AI with Docker

## Quick start

From the project root (where `docker-compose.yml` lives):

```bash
docker compose up --build
```

Then open **http://localhost** in your browser. The frontend is served on port 80 and proxies `/api` to the backend.

Ensure `backend/.env` exists with your API keys (see `backend/.env` or copy from your existing setup):

- `GEMINI_API_KEY` — for mood/profile and recommendations
- `WEATHER_API_KEY` — for weather context (optional; backend falls back if missing)

---

## Docker runtime options (Desktop vs alternatives)

| Option | Best for | Notes |
|--------|----------|--------|
| **Docker Desktop** | Windows/Mac users who want a single install (Engine + UI + Compose) | Easiest on Windows/Mac. Includes Docker Compose and a GUI. Free for personal/small business; paid for larger companies. |
| **Docker Engine + CLI** | Linux or minimal setups | Install `docker` and `docker compose` (or `docker-compose`) only. No GUI. Free and lightweight. |
| **Rancher Desktop** | Alternative to Docker Desktop (no license concerns) | Open source, free. Uses containerd by default; can switch to Docker (moby). Good on Windows/Mac. |
| **Podman** | Rootless / daemonless / CI | CLI-compatible with Docker. `podman compose` works with this project. No daemon; good for servers and automation. |

**Recommendation**

- **Windows (your setup):** **Docker Desktop** is the simplest: install, run “Docker Desktop”, then `docker compose up --build` in this repo. If you prefer open source or want to avoid Docker Desktop’s license, use **Rancher Desktop** and run the same `docker compose` commands.
- **Linux:** Use **Docker Engine** (`docker` + `docker compose` plugin) from your distro’s packages.
- **CI / headless:** Use **Docker Engine** or **Podman** with `docker compose` / `podman compose`.

All of these can build and run the same `Dockerfile` and `docker-compose.yml` in this project.

---

## Compose layout

- **backend** — FastAPI app (uvicorn). No port published; only the frontend talks to it.
- **frontend** — Vue (Vite) build served by nginx; proxies `/api` to the backend. Port **80** is published.

To run only the backend (e.g. for local frontend dev):

```bash
docker compose up --build backend
```

Then run the frontend with `npm run dev` in `frontend/` and use the dev proxy to `http://localhost:8000`.
