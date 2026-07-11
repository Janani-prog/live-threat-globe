"""Loads the trained risk-scoring artifact once and exposes score()."""

import datetime
import logging
from pathlib import Path

import joblib

from app.ml.features import build_feature_dict

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"

_artifact = None


def _load():
    global _artifact
    if _artifact is None:
        if not MODEL_PATH.exists():
            logger.warning("No trained model artifact at %s — risk scoring disabled", MODEL_PATH)
            return None
        _artifact = joblib.load(MODEL_PATH)
    return _artifact


def score(
    total_reports: int,
    num_distinct_users: int,
    category_ids: list[int],
    usage_type: str | None,
    last_reported_at: datetime.datetime | None,
    country: str | None,
) -> float | None:
    """Return a 0-100 risk score, or None if no model artifact is available."""
    artifact = _load()
    if artifact is None:
        return None

    prior = artifact["country_priors"].get(country or "UNKNOWN", artifact["global_prior"])
    features = build_feature_dict(
        total_reports=total_reports,
        num_distinct_users=num_distinct_users,
        category_ids=category_ids,
        usage_type=usage_type,
        last_reported_at=last_reported_at,
        country_risk_prior=prior,
    )
    vector = [[features[col] for col in artifact["feature_columns"]]]
    proba = artifact["pipeline"].predict_proba(vector)[0][1]
    return round(float(proba) * 100, 2)
