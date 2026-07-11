import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.cloudflare.com/client/v4"


def fetch_attack_trends(date_range: str = "7d") -> dict | None:
    """Fetch aggregate L3 attack-layer trend data (timeseries + top origin countries).

    This is aggregate, non-per-IP data — feeds the stats dashboard, not the globe
    markers (per Technical Architecture doc section 3/6).
    """
    if not settings.cloudflare_radar_api_token:
        logger.error("CLOUDFLARE_RADAR_API_TOKEN is not set — skipping Cloudflare Radar poll")
        return None

    headers = {"Authorization": f"Bearer {settings.cloudflare_radar_api_token}"}

    try:
        timeseries_resp = httpx.get(
            f"{BASE_URL}/radar/attacks/layer3/timeseries",
            headers=headers,
            params={"dateRange": date_range},
            timeout=10,
        )
        top_origin_resp = httpx.get(
            f"{BASE_URL}/radar/attacks/layer3/top/locations/origin",
            headers=headers,
            params={"dateRange": date_range, "limit": 10},
            timeout=10,
        )
    except httpx.HTTPError as exc:
        logger.error("Cloudflare Radar request failed: %s", exc)
        return None

    for resp in (timeseries_resp, top_origin_resp):
        if resp.status_code == 429:
            logger.warning("Cloudflare Radar rate limit hit — backing off until next scheduled poll")
            return None
        if resp.status_code != 200:
            logger.error("Cloudflare Radar returned unexpected status %s", resp.status_code)
            return None

    return {
        "timeseries": timeseries_resp.json().get("result", {}),
        "top_origin_countries": top_origin_resp.json().get("result", {}).get("top_0", []),
    }
