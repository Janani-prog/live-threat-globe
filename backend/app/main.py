import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.config import settings
from app.db.session import init_db
from app.rate_limit import limiter
from app.realtime.manager import manager
from app.realtime.router import router as realtime_router
from app.scheduler import create_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    manager.set_loop(asyncio.get_running_loop())

    scheduler = create_scheduler()
    if settings.enable_scheduler:
        scheduler.start()
    app.state.scheduler = scheduler

    try:
        yield
    finally:
        if settings.enable_scheduler:
            scheduler.shutdown(wait=False)


app = FastAPI(title="CyberPulse API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # No stack traces to clients (Security & Access doc section 4) — full
    # traceback goes to server-side logs only.
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(api_router)
app.include_router(realtime_router)

# Built frontend static assets (Technical Architecture doc section 7: one
# service serves the API, WebSocket, and the built frontend). Populated by
# the Dockerfile's frontend build stage; absent in local dev unless someone
# manually builds+copies it there, so mount conditionally rather than
# crashing the whole app on startup — the JSON API/WebSocket routes above
# still work fine without it, this only affects serving the UI itself.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
else:
    logger.warning("No built frontend found at %s — API/WebSocket routes only", STATIC_DIR)
