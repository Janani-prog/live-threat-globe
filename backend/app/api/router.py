from fastapi import APIRouter

from app.api import events, health, stats

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(events.router)
api_router.include_router(stats.router)
