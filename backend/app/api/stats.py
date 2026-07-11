import datetime
from collections import Counter

from fastapi import APIRouter, Query, Request
from sqlalchemy import func, select

from app import scheduler
from app.api.schemas import CountBucket, StatsSummary, TimeseriesOut, TimeseriesPoint
from app.db.models import Event
from app.db.session import get_session
from app.rate_limit import limiter

router = APIRouter()


@router.get("/stats/summary", response_model=StatsSummary)
@limiter.limit("30/minute")
def get_stats_summary(request: Request):
    session = get_session()
    try:
        total = session.execute(select(func.count(Event.id))).scalar_one()

        country_rows = session.execute(
            select(Event.country, func.count(Event.id))
            .where(Event.country.is_not(None))
            .group_by(Event.country)
            .order_by(func.count(Event.id).desc())
            .limit(10)
        ).all()
        top_countries = [CountBucket(key=c, count=n) for c, n in country_rows]

        asn_rows = session.execute(
            select(Event.asn, func.count(Event.id))
            .where(Event.asn.is_not(None))
            .group_by(Event.asn)
            .order_by(func.count(Event.id).desc())
            .limit(10)
        ).all()
        top_asns = [CountBucket(key=a, count=n) for a, n in asn_rows]

        category_counter: Counter = Counter()
        cat_rows = session.execute(select(Event.category).where(Event.category.is_not(None))).scalars().all()
        for cat_str in cat_rows:
            for cid in cat_str.split(","):
                if cid:
                    category_counter[cid] += 1
        category_breakdown = [CountBucket(key=cid, count=n) for cid, n in category_counter.most_common(10)]
    finally:
        session.close()

    cf_countries = None
    if scheduler.latest_radar_snapshot:
        cf_countries = scheduler.latest_radar_snapshot.get("top_origin_countries")

    return StatsSummary(
        total_events=total,
        top_countries=top_countries,
        top_asns=top_asns,
        category_breakdown=category_breakdown,
        cloudflare_top_origin_countries=cf_countries,
    )


@router.get("/stats/timeseries", response_model=TimeseriesOut)
@limiter.limit("30/minute")
def get_stats_timeseries(request: Request, minutes: int = Query(60, ge=1, le=1440)):
    session = get_session()
    try:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes)
        rows = session.execute(select(Event.ingested_at).where(Event.ingested_at >= cutoff)).scalars().all()
    finally:
        session.close()

    buckets: Counter = Counter()
    for ts in rows:
        bucket = ts.replace(second=0, microsecond=0)
        buckets[bucket] += 1

    points = [TimeseriesPoint(bucket=b, count=c) for b, c in sorted(buckets.items())]
    return TimeseriesOut(points=points)
