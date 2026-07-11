import datetime
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BLACKLIST_URL = "https://api.abuseipdb.com/api/v2/blacklist"
CHECK_URL = "https://api.abuseipdb.com/api/v2/check"

# /check shares a 1,000-req/day free-tier quota (confirmed via x-ratelimit-limit
# response header) — separate from /blacklist. Pace calls conservatively; this
# isn't a documented per-second limit, just a courtesy to avoid bursting.
_MIN_CHECK_INTERVAL = 0.3
_last_check_at = 0.0


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


class CheckResult:
    def __init__(
        self,
        ip: str,
        total_reports: int,
        num_distinct_users: int,
        category_ids: list[int],
        usage_type: str | None,
        last_reported_at: datetime.datetime | None,
        abuse_confidence_score: float,
        country: str | None = None,
    ):
        self.ip = ip
        self.total_reports = total_reports
        self.num_distinct_users = num_distinct_users
        self.category_ids = category_ids
        self.usage_type = usage_type
        self.last_reported_at = last_reported_at
        self.abuse_confidence_score = abuse_confidence_score
        self.country = country


def check_ip(ip: str) -> CheckResult | None:
    """Call /check?verbose for a single IP — the only endpoint that exposes
    category codes, total report count, distinct-reporter count, and usage
    type (used for both ML feature engineering and the proxy label).
    Quota-limited (1,000/day free tier), so callers must only invoke this for
    genuinely new/unseen IPs, never the whole blacklist.
    """
    if not settings.abuseipdb_api_key:
        logger.error("ABUSEIPDB_API_KEY is not set — skipping /check call")
        return None

    global _last_check_at
    elapsed = time.monotonic() - _last_check_at
    if elapsed < _MIN_CHECK_INTERVAL:
        time.sleep(_MIN_CHECK_INTERVAL - elapsed)
    _last_check_at = time.monotonic()

    headers = {"Key": settings.abuseipdb_api_key, "Accept": "application/json"}
    params = {"ipAddress": ip, "verbose": ""}

    try:
        resp = httpx.get(CHECK_URL, headers=headers, params=params, timeout=10)
    except httpx.HTTPError as exc:
        logger.warning("AbuseIPDB /check request failed for an IP: %s", exc)
        return None

    if resp.status_code == 429:
        logger.warning("AbuseIPDB /check quota/rate limit hit — skipping this IP")
        return None
    if resp.status_code == 401:
        logger.error("AbuseIPDB rejected the API key (401) — check ABUSEIPDB_API_KEY")
        return None
    if resp.status_code != 200:
        logger.warning("AbuseIPDB /check returned unexpected status %s", resp.status_code)
        return None

    data = resp.json().get("data", {})
    category_ids: set[int] = set()
    for report in data.get("reports", []):
        category_ids.update(report.get("categories", []))

    last_reported_at = None
    if data.get("lastReportedAt"):
        try:
            last_reported_at = datetime.datetime.fromisoformat(data["lastReportedAt"])
        except ValueError:
            last_reported_at = None

    return CheckResult(
        ip=ip,
        total_reports=data.get("totalReports", 0),
        num_distinct_users=data.get("numDistinctUsers", 0),
        category_ids=sorted(category_ids),
        usage_type=data.get("usageType"),
        last_reported_at=last_reported_at,
        abuse_confidence_score=data.get("abuseConfidenceScore", 0),
        country=data.get("countryCode"),
    )
