import collections
import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import BLACKLIST_DAILY_SAFE_MAX, settings
from app.db.models import ApiQuotaUsage, Event
from app.db.session import get_session
from app.geo.client import geolocate
from app.geo.hashing import hash_ip
from app.ingestion import abuseipdb, cloudflare_radar
from app.ml import scorer
from app.realtime.manager import manager

logger = logging.getLogger(__name__)

CLOUDFLARE_POLL_MULTIPLIER = 5  # Radar data is aggregate/slow-moving, poll it less often

# /check has a much more generous 1,000/day free-tier quota than /blacklist's
# 5/day, but a naive "check every newly drained IP" could still burn through
# it fast if the backlog is large. Guard it too, with headroom left over for
# manual training pulls / dev testing on the same day.
CHECK_DAILY_SAFE_MAX = 800

# Backlog pattern: /blacklist can only be called a few times/day (quota-
# guarded below), but each call can return a large batch. Queue newly-seen
# IPs here and drain them a few at a time on the existing fast (~30s) tick,
# so the globe keeps animating between infrequent source refreshes instead
# of going quiet for hours. This matches the PRD's own framing of the feed
# as "a periodically polled, rate-limited sample... presented as a
# live-feeling stream" — not a new claim, just how that's implemented.
_backlog: collections.deque = collections.deque()
_MAX_BACKLOG = 5000  # bounded so one big pull can't grow this unboundedly

latest_radar_snapshot: dict | None = None


def _today() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")


def _try_consume_quota(session, column: str, safe_max: int) -> bool:
    """Atomically check-and-increment a per-day call counter persisted in
    SQLite (survives process restarts, unlike an in-memory counter)."""
    today = _today()
    row = session.get(ApiQuotaUsage, today)
    if row is None:
        row = ApiQuotaUsage(date=today, blacklist_calls=0, check_calls=0)
        session.add(row)
        session.flush()
    current = getattr(row, column)
    if current >= safe_max:
        return False
    setattr(row, column, current + 1)
    session.commit()
    return True


def run_blacklist_pull_cycle() -> int:
    """Pull a large batch from /blacklist (quota-guarded) and queue genuinely
    new IPs into the in-memory backlog for run_drain_cycle to process.
    """
    session = get_session()
    try:
        if not _try_consume_quota(session, "blacklist_calls", BLACKLIST_DAILY_SAFE_MAX):
            logger.warning(
                "Blacklist daily quota guard hit (%d/day) — skipping pull until tomorrow (UTC)",
                BLACKLIST_DAILY_SAFE_MAX,
            )
            return 0

        events = abuseipdb.fetch_blacklist(limit=settings.blacklist_fetch_limit)
        queued = 0
        for evt in events:
            ip_hash = hash_ip(evt.ip)
            already_seen = session.execute(select(Event.id).where(Event.ip_hash == ip_hash).limit(1)).first()
            if already_seen:
                continue
            if len(_backlog) >= _MAX_BACKLOG:
                logger.warning("Backlog full (%d) — dropping remaining candidates from this pull", _MAX_BACKLOG)
                break
            _backlog.append(evt)
            queued += 1
    finally:
        session.close()

    logger.info("Blacklist pull queued %d new IP(s) (backlog size now %d)", queued, len(_backlog))
    return queued


def run_drain_cycle() -> int:
    """Pop one queued IP, geolocate + risk-score it, and persist it. Runs on
    the fast (~30s) cadence. /check (needed for ML features) is
    quota-guarded independently of /blacklist, so under quota exhaustion the
    event still gets stored (with geolocation) but without a risk score,
    rather than being dropped — graceful degradation, not a crash.
    """
    if not _backlog:
        return 0

    evt = _backlog.popleft()
    session = get_session()
    try:
        ip_hash = hash_ip(evt.ip)
        already_seen = session.execute(select(Event.id).where(Event.ip_hash == ip_hash).limit(1)).first()
        if already_seen:
            return 0

        geo = geolocate(evt.ip, session)
        country = geo["country"] if geo else evt.country

        category_str = None
        risk_score = None
        if _try_consume_quota(session, "check_calls", CHECK_DAILY_SAFE_MAX):
            check_result = abuseipdb.check_ip(evt.ip)
            if check_result is not None:
                category_str = ",".join(str(c) for c in check_result.category_ids) or None
                risk_score = scorer.score(
                    total_reports=check_result.total_reports,
                    num_distinct_users=check_result.num_distinct_users,
                    category_ids=check_result.category_ids,
                    usage_type=check_result.usage_type,
                    last_reported_at=check_result.last_reported_at,
                    country=country,
                )
        else:
            logger.debug(
                "Check daily quota guard hit (%d/day) — storing event without ML features", CHECK_DAILY_SAFE_MAX
            )

        event_row = Event(
            ip_hash=ip_hash,
            lat=geo["lat"] if geo else None,
            lon=geo["lon"] if geo else None,
            country=country,
            asn=geo["asn"] if geo else None,
            category=category_str,
            confidence_source=evt.confidence_score,
            risk_score=risk_score,
            reported_at=evt.reported_at,
        )
        session.add(event_row)
        session.commit()

        # expire_on_commit=False (see app.db.session) keeps these attributes
        # readable post-commit without a second query.
        payload = {
            "id": event_row.id,
            "ip_hash": event_row.ip_hash,
            "lat": event_row.lat,
            "lon": event_row.lon,
            "country": event_row.country,
            "asn": event_row.asn,
            "category": event_row.category,
            "confidence_source": event_row.confidence_source,
            # May be None if no trained model exists yet or the /check quota
            # guard was hit — the WebSocket payload serializes this as JSON
            # null; consumers must treat that as "not yet scored", not 0.
            "risk_score": event_row.risk_score,
            "reported_at": event_row.reported_at.isoformat() if event_row.reported_at else None,
            "ingested_at": event_row.ingested_at.isoformat() if event_row.ingested_at else None,
        }
    finally:
        session.close()

    manager.broadcast_from_thread(payload)
    return 1


def run_cloudflare_radar_cycle() -> None:
    global latest_radar_snapshot
    snapshot = cloudflare_radar.fetch_attack_trends()
    if snapshot is not None:
        latest_radar_snapshot = snapshot
        logger.info("Cloudflare Radar snapshot refreshed")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    interval = settings.poll_interval_seconds
    scheduler.add_job(run_blacklist_pull_cycle, "interval", seconds=settings.blacklist_poll_seconds, id="blacklist_pull")
    scheduler.add_job(run_drain_cycle, "interval", seconds=interval, id="backlog_drain")
    scheduler.add_job(
        run_cloudflare_radar_cycle,
        "interval",
        seconds=interval * CLOUDFLARE_POLL_MULTIPLIER,
        id="cloudflare_radar_poll",
    )
    return scheduler
