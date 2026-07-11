"""Feature engineering for the live composite risk scorer.

Inputs come from AbuseIPDB's /check?verbose response (see
app.ingestion.abuseipdb.check_ip), not the bulk /blacklist response, which
lacks category/report-count data (confirmed in Phase 1).
"""

import datetime

# AbuseIPDB's published category list (https://www.abuseipdb.com/categories).
# IDs are stable/documented, not an API response — used here purely to label
# the multi-hot category columns below.
ABUSEIPDB_CATEGORIES: dict[int, str] = {
    1: "dns_compromise",
    2: "dns_poisoning",
    3: "fraud_orders",
    4: "ddos_attack",
    5: "ftp_brute_force",
    6: "ping_of_death",
    7: "phishing",
    8: "fraud_voip",
    9: "open_proxy",
    10: "web_spam",
    11: "email_spam",
    12: "blog_spam",
    13: "vpn_ip",
    14: "port_scan",
    15: "hacking",
    16: "sql_injection",
    17: "spoofing",
    18: "brute_force",
    19: "bad_web_bot",
    20: "exploited_host",
    21: "web_app_attack",
    22: "ssh",
    23: "iot_targeted",
}
CATEGORY_IDS_SORTED = sorted(ABUSEIPDB_CATEGORIES)

# Proxy label. Technical Architecture doc 5a originally specified positive =
# categories intersect {DDoS(4), Port-Scan(14), Brute-Force(18)}. Verified
# against a real AbuseIPDB /check pull (Phase 2) and reverted: category 18
# (Brute-Force) appeared on 100% of a 300-sample pull and category 14
# (Port-Scan) on ~92% of a diagnostic 60-sample pull — both are bundled onto
# nearly every blacklisted IP's report, making the original definition
# ~100% positive and non-discriminative (a 300/300-positive training pull
# is what surfaced this). Narrowed to category 4 (DDoS Attack) alone, which
# gave a real ~38% positive rate in the same diagnostic pull and matches the
# project's actual purpose (DDoS-relevance scoring, not generic-abuse
# scoring). No live ground-truth "is this a DDoS source" label exists
# either way — this remains a documented weak/proxy-supervision choice.
PROXY_LABEL_CATEGORY_IDS = {4}

# ASN/usage-type bucketing, based on AbuseIPDB's own `usageType` field
# (returned by /check) rather than a hand-curated ASN list.
_HOSTING_USAGE_TYPES = {"Data Center/Web Hosting/Transit", "Content Delivery Network"}
_ISP_USAGE_TYPES = {"Fixed Line ISP", "Mobile ISP"}

NUMERIC_FEATURE_COLUMNS = [
    "total_reports",
    "num_distinct_users",
    "days_since_last_report",
    "usage_type_hosting",
    "usage_type_isp",
    "usage_type_other",
    "country_risk_prior",
]
CATEGORY_FEATURE_COLUMNS = [f"category_{cid}" for cid in CATEGORY_IDS_SORTED]
FEATURE_COLUMNS = NUMERIC_FEATURE_COLUMNS + CATEGORY_FEATURE_COLUMNS


def usage_type_bucket(usage_type: str | None) -> str:
    if usage_type in _HOSTING_USAGE_TYPES:
        return "hosting"
    if usage_type in _ISP_USAGE_TYPES:
        return "isp"
    return "other"


def proxy_label(category_ids: list[int]) -> int:
    return int(bool(PROXY_LABEL_CATEGORY_IDS & set(category_ids)))


def build_feature_dict(
    total_reports: int,
    num_distinct_users: int,
    category_ids: list[int],
    usage_type: str | None,
    last_reported_at: datetime.datetime | None,
    country_risk_prior: float,
) -> dict[str, float]:
    if last_reported_at is not None:
        now = datetime.datetime.now(last_reported_at.tzinfo) if last_reported_at.tzinfo else datetime.datetime.utcnow()
        days_since = max((now - last_reported_at).total_seconds() / 86400, 0.0)
    else:
        days_since = 365.0  # unknown recency treated as stale

    bucket = usage_type_bucket(usage_type)
    features: dict[str, float] = {
        "total_reports": float(total_reports),
        "num_distinct_users": float(num_distinct_users),
        "days_since_last_report": days_since,
        "usage_type_hosting": float(bucket == "hosting"),
        "usage_type_isp": float(bucket == "isp"),
        "usage_type_other": float(bucket == "other"),
        "country_risk_prior": country_risk_prior,
    }
    cat_set = set(category_ids)
    for cid in CATEGORY_IDS_SORTED:
        features[f"category_{cid}"] = float(cid in cat_set)
    return features


def to_feature_vector(feature_dict: dict[str, float]) -> list[float]:
    return [feature_dict[col] for col in FEATURE_COLUMNS]
