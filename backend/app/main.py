"""Visual Barista AI — FastAPI app."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.debug import router as debug_router
from app.routes.feedback import router as feedback_router
from app.routes.recommendation import router as recommendation_router
from app.routes.weather import router as weather_router
from app.services.menu_service import get_full_menu

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "A multimodal recommendation engine that suggests coffee drinks "
        "based on user mood, weather, and time of day."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommendation_router)
app.include_router(debug_router)
app.include_router(feedback_router)
app.include_router(weather_router)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/menu", tags=["Menu"])
async def list_menu() -> list[dict]:
    return get_full_menu()
