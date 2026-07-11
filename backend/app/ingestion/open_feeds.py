"""Free, non-rate-limited IP reputation feeds used as an alternative
candidate-IP source for ML training data collection (app/ml/training/train.py).

Not used by the live ingestion pipeline (app/scheduler.py) — that's
AbuseIPDB's /blacklist, per the architecture doc. This module exists solely
because /blacklist is capped at 5 requests/day (see CLAUDE.md), which blocks
pulling a fresh, diverse training batch on demand. These feeds have no such
cap and are updated continuously, so they're a good source of *candidate*
IPs — the actual feature data (report counts, categories, etc.) still comes
from a real AbuseIPDB /check call per candidate, same as before. No feature
data is invented; only the discovery mechanism for which IPs to look up
changes.

Bonus methodological benefit: AbuseIPDB's own /blacklist is pre-filtered to
IPs it already has substantial report history on, which skewed an earlier
training pull to ~100% positive on the DDoS-category proxy label (see
features.py). These feeds are curated independently (SSH/mail/web attack
reporting for Blocklist.de, a broader reputation score for CINS Army), so
checking them against AbuseIPDB naturally includes some IPs AbuseIPDB has
sparse or no data on — real negative-leaning examples, not synthetic ones.
"""

import logging
import random

import httpx

logger = logging.getLogger(__name__)

BLOCKLIST_DE_URL = "https://lists.blocklist.de/lists/all.txt"
CINSSCORE_URL = "http://cinsscore.com/list/ci-badguys.txt"

# Human-readable source labels, used both for logging and (via scheduler.py)
# surfaced to the frontend so the UI can show a real provenance label per
# event rather than a hardcoded/fabricated one.
BLOCKLIST_DE_LABEL = "Blocklist.de"
CINSSCORE_LABEL = "CINS Army"


def _fetch_ip_list(url: str) -> list[str]:
    try:
        resp = httpx.get(url, timeout=15)
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch open feed %s: %s", url, exc)
        return []

    if resp.status_code != 200:
        logger.warning("Open feed %s returned status %s", url, resp.status_code)
        return []

    ips = [line.strip() for line in resp.text.splitlines() if line.strip()]
    logger.info("Fetched %d IPs from %s", len(ips), url)
    return ips


def sample_candidate_ips_with_source(n: int, seed: int | None = None) -> list[tuple[str, str]]:
    """Fetch and combine Blocklist.de + CINSScore, dedupe, and return a
    random sample of up to n (ip, source_label) pairs (mixed across both
    sources for diversity). The source label is real provenance, not a
    display placeholder — it reflects which feed actually returned the IP.
    """
    blocklist_de = [(ip, BLOCKLIST_DE_LABEL) for ip in _fetch_ip_list(BLOCKLIST_DE_URL)]
    cinsscore = [(ip, CINSSCORE_LABEL) for ip in _fetch_ip_list(CINSSCORE_URL)]

    combined_map: dict[str, str] = {}
    for ip, label in blocklist_de + cinsscore:
        combined_map.setdefault(ip, label)  # first source wins on duplicate IP
    combined = list(combined_map.items())
    logger.info("Combined open-feed candidate pool: %d unique IPs", len(combined))

    rng = random.Random(seed)
    rng.shuffle(combined)
    return combined[:n]


def sample_candidate_ips(n: int, seed: int | None = None) -> list[str]:
    """Backward-compatible plain-IP variant, used by the ML training
    pipeline (app/ml/training/train.py), which doesn't need provenance."""
    return [ip for ip, _label in sample_candidate_ips_with_source(n, seed)]
