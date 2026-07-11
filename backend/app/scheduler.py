import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import settings
from app.db.models import Event
from app.db.session import get_session
from app.geo.client import geolocate
from app.ingestion import abuseipdb, cloudflare_radar
from app.geo.hashing import hash_ip

logger = logging.getLogger(__name__)

CLOUDFLARE_POLL_MULTIPLIER = 5  # Radar data is aggregate/slow-moving, poll it less often

latest_radar_snapshot: dict | None = None


def run_abuseipdb_cycle() -> int:
    """Run one ingest -> geolocate -> persist cycle. Returns the number of new events stored."""
    session = get_session()
    stored = 0
    try:
        events = abuseipdb.fetch_blacklist()
        for evt in events:
            ip_hash = hash_ip(evt.ip)

            already_seen = session.execute(
                select(Event.id).where(Event.ip_hash == ip_hash).limit(1)
            ).first()
            if already_seen:
                continue

            geo = geolocate(evt.ip, session)

            session.add(
                Event(
                    ip_hash=ip_hash,
                    lat=geo["lat"] if geo else None,
                    lon=geo["lon"] if geo else None,
                    country=(geo["country"] if geo else evt.country),
                    asn=geo["asn"] if geo else None,
                    category=None,
                    confidence_source=evt.confidence_score,
                    risk_score=None,
                    reported_at=evt.reported_at,
                )
            )
            stored += 1
        session.commit()
    finally:
        session.close()

    logger.info("AbuseIPDB ingest cycle stored %d new event(s)", stored)
    return stored


def run_cloudflare_radar_cycle() -> None:
    global latest_radar_snapshot
    snapshot = cloudflare_radar.fetch_attack_trends()
    if snapshot is not None:
        latest_radar_snapshot = snapshot
        logger.info("Cloudflare Radar snapshot refreshed")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    interval = settings.poll_interval_seconds
    scheduler.add_job(run_abuseipdb_cycle, "interval", seconds=interval, id="abuseipdb_ingest")
    scheduler.add_job(
        run_cloudflare_radar_cycle,
        "interval",
        seconds=interval * CLOUDFLARE_POLL_MULTIPLIER,
        id="cloudflare_radar_poll",
    )
    return scheduler
