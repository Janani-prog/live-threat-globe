from fastapi import APIRouter, Request

from app.ml import scorer
from app.rate_limit import limiter

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/health/pipeline")
@limiter.limit("30/minute")
def pipeline_health(request: Request):
    """Real backend pipeline status for the frontend's diagnostics view —
    every field here reflects actual runtime state, not a hardcoded string
    that would keep claiming success if the scheduler or model failed.
    """
    scheduler = getattr(request.app.state, "scheduler", None)
    ingestion_active = bool(scheduler is not None and scheduler.running)

    return {
        "ingestion_engine": {"active": ingestion_active},
        "ml_classifier": scorer.status(),
    }
