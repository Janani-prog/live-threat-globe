import datetime
import logging
import time

import httpx
from sqlalchemy.orm import Session

from app.db.models import GeoCache
from app.geo.hashing import hash_ip

logger = logging.getLogger(__name__)

GEO_CACHE_TTL = datetime.timedelta(hours=24)
IP_API_URL = "http://ip-api.com/json/{ip}"

# ip-api.com free tier allows 45 requests/minute; pace calls to stay under that
# instead of relying solely on 429 backoff (avoids silently dropping geo data
# on the first cold-start burst of many new IPs).
_MIN_REQUEST_INTERVAL = 60 / 40
_last_request_at = 0.0


def _throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_at = time.monotonic()


def _fetch_live(ip: str) -> dict | None:
    _throttle()
    try:
        resp = httpx.get(IP_API_URL.format(ip=ip), params={"fields": "status,lat,lon,countryCode,as"}, timeout=5)
    except httpx.HTTPError as exc:
        logger.warning("geolocation request failed for an IP: %s", exc)
        return None

    if resp.status_code == 429:
        logger.warning("geolocation rate limit hit (ip-api.com), skipping this IP for now")
        return None
    if resp.status_code != 200:
        logger.warning("geolocation lookup returned status %s", resp.status_code)
        return None

    data = resp.json()
    if data.get("status") != "success":
        return None

    return {
        "lat": data.get("lat"),
        "lon": data.get("lon"),
        "country": data.get("countryCode"),
        "asn": data.get("as"),
    }


def geolocate(ip: str, session: Session) -> dict | None:
    """Return {lat, lon, country, asn} for a raw IP, using the SQLite cache first.

    The raw IP is only used transiently here (to key the cache by its hash and,
    on a cache miss, to call the geolocation API) — it is never persisted.
    """
    ip_hash = hash_ip(ip)
    cached = session.get(GeoCache, ip_hash)
    now = datetime.datetime.utcnow()

    if cached and (now - cached.last_checked_at) < GEO_CACHE_TTL:
        return {"lat": cached.lat, "lon": cached.lon, "country": cached.country, "asn": cached.asn}

    result = _fetch_live(ip)
    if result is None:
        if cached:
            return {"lat": cached.lat, "lon": cached.lon, "country": cached.country, "asn": cached.asn}
        return None

    if cached:
        cached.lat = result["lat"]
        cached.lon = result["lon"]
        cached.country = result["country"]
        cached.asn = result["asn"]
        cached.last_checked_at = now
    else:
        session.add(
            GeoCache(
                ip_hash=ip_hash,
                lat=result["lat"],
                lon=result["lon"],
                country=result["country"],
                asn=result["asn"],
                last_checked_at=now,
            )
        )
    session.commit()
    return result
