import datetime
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BLACKLIST_URL = "https://api.abuseipdb.com/api/v2/blacklist"


class NormalizedEvent:
    def __init__(self, ip: str, country: str | None, confidence_score: float, reported_at: datetime.datetime | None):
        self.ip = ip
        self.country = country
        self.confidence_score = confidence_score
        self.reported_at = reported_at


def fetch_blacklist(limit: int = 100, confidence_minimum: int = 75) -> list[NormalizedEvent]:
    """Fetch the AbuseIPDB blacklist and normalize it into internal events.

    Note: the bulk /blacklist endpoint only returns ipAddress, countryCode,
    abuseConfidenceScore, lastReportedAt — no category codes or report counts.
    Those richer per-IP fields (used for ML features in Phase 2) require a
    separate call to /check, which shares a much tighter free-tier quota, so
    they're only fetched for genuinely new IPs, not the whole blacklist.
    """
    if not settings.abuseipdb_api_key:
        logger.error("ABUSEIPDB_API_KEY is not set — skipping AbuseIPDB poll")
        return []

    headers = {"Key": settings.abuseipdb_api_key, "Accept": "application/json"}
    params = {"limit": limit, "confidenceMinimum": confidence_minimum}

    try:
        resp = httpx.get(BLACKLIST_URL, headers=headers, params=params, timeout=10)
    except httpx.HTTPError as exc:
        logger.error("AbuseIPDB request failed: %s", exc)
        return []

    if resp.status_code == 429:
        logger.warning("AbuseIPDB rate limit hit — backing off until next scheduled poll")
        return []
    if resp.status_code == 401:
        logger.error("AbuseIPDB rejected the API key (401) — check ABUSEIPDB_API_KEY")
        return []
    if resp.status_code != 200:
        logger.error("AbuseIPDB returned unexpected status %s", resp.status_code)
        return []

    body = resp.json()
    events: list[NormalizedEvent] = []
    for row in body.get("data", []):
        reported_at = None
        if row.get("lastReportedAt"):
            try:
                reported_at = datetime.datetime.fromisoformat(row["lastReportedAt"])
            except ValueError:
                reported_at = None
        events.append(
            NormalizedEvent(
                ip=row["ipAddress"],
                country=row.get("countryCode"),
                confidence_score=row.get("abuseConfidenceScore", 0),
                reported_at=reported_at,
            )
        )
    return events
