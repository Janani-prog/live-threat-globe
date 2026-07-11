from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from app.api.schemas import EventOut
from app.db.models import Event
from app.db.session import get_session
from app.rate_limit import limiter

router = APIRouter()


@router.get("/events/recent", response_model=list[EventOut])
@limiter.limit("30/minute")
def get_recent_events(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    session = get_session()
    try:
        rows = (
            session.execute(select(Event).order_by(Event.id.desc()).offset(offset).limit(limit))
            .scalars()
            .all()
        )
        return rows
    finally:
        session.close()
