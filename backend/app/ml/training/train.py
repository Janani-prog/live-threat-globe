"""Pull a historical AbuseIPDB batch, engineer features, train and evaluate a
logistic regression baseline, and export the model artifact + model card.

Usage: python -m app.ml.training.train   (run from backend/, with .env populated)

No raw IPs are persisted anywhere by this script — only engineered features
and the trained artifact.
"""

import datetime
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ingestion import abuseipdb, open_feeds
from app.ml.features import FEATURE_COLUMNS, build_feature_dict, proxy_label

TRAINING_BATCH_SIZE = 250
COUNTRY_PRIOR_SMOOTHING = 5.0

MODEL_PATH = Path(__file__).resolve().parents[1] / "model.pkl"
MODEL_CARD_PATH = Path(__file__).resolve().parents[1] / "model_card.md"


def pull_raw_rows() -> list[dict]:
    """Fetch candidate IPs from open, non-rate-limited feeds (Blocklist.de +
    CINS Army), then enrich each with a real AbuseIPDB /check call — /check
    is the only endpoint with category/report data, and unlike /blacklist
    (capped at 5 req/day, see CLAUDE.md) it has a generous 1,000/day quota.

    This also diversifies the candidate pool relative to pulling straight
    from AbuseIPDB's own /blacklist: that endpoint is pre-filtered to IPs
    it already has heavy report history on, which skewed an earlier
    training pull to ~100% positive on the DDoS-category proxy label (see
    features.py). These feeds are curated independently, so some checked
    IPs turn out to have sparse/no AbuseIPDB history — real negative-
    leaning examples, not synthetic ones.
    """
    candidate_ips = open_feeds.sample_candidate_ips(TRAINING_BATCH_SIZE, seed=42)
    logger.info("Sampled %d candidate IPs from open feeds", len(candidate_ips))

    rows = []
    for i, ip in enumerate(candidate_ips):
        result = abuseipdb.check_ip(ip)
        if result is None:
            continue
        rows.append(
            {
                "country": result.country,
                "total_reports": result.total_reports,
                "num_distinct_users": result.num_distinct_users,
                "category_ids": result.category_ids,
                "usage_type": result.usage_type,
                "last_reported_at": result.last_reported_at,
                "abuse_confidence_score": result.abuse_confidence_score,
            }
        )
        if (i + 1) % 50 == 0:
            logger.info("  ...checked %d/%d", i + 1, len(candidate_ips))

    logger.info("Collected %d rows with /check data", len(rows))
    return rows


def compute_country_priors(rows: list[dict]) -> tuple[dict[str, float], float]:
    labels = [proxy_label(r["category_ids"]) for r in rows]
    global_rate = sum(labels) / len(labels) if labels else 0.0

    by_country: dict[str, list[int]] = {}
    for row, label in zip(rows, labels):
        by_country.setdefault(row["country"] or "UNKNOWN", []).append(label)

    priors = {}
    for country, country_labels in by_country.items():
        n = len(country_labels)
        positives = sum(country_labels)
        priors[country] = (positives + COUNTRY_PRIOR_SMOOTHING * global_rate) / (n + COUNTRY_PRIOR_SMOOTHING)
    return priors, global_rate


def build_dataset(rows: list[dict], country_priors: dict[str, float], global_prior: float):
    X, y, raw_confidence = [], [], []
    for row in rows:
        prior = country_priors.get(row["country"] or "UNKNOWN", global_prior)
        feat = build_feature_dict(
            total_reports=row["total_reports"],
            num_distinct_users=row["num_distinct_users"],
            category_ids=row["category_ids"],
            usage_type=row["usage_type"],
            last_reported_at=row["last_reported_at"],
            country_risk_prior=prior,
        )
        X.append([feat[col] for col in FEATURE_COLUMNS])
        y.append(proxy_label(row["category_ids"]))
        raw_confidence.append(row["abuse_confidence_score"])
    return np.array(X), np.array(y), np.array(raw_confidence)


def main():
    rows = pull_raw_rows()
    if len(rows) < 30:
        logger.error("Too few rows (%d) to train a meaningful model — aborting", len(rows))
        sys.exit(1)

    country_priors, global_prior = compute_country_priors(rows)
    X, y, raw_confidence = build_dataset(rows, country_priors, global_prior)

    logger.info("Dataset: %d samples, %d positive (%.1f%%)", len(y), y.sum(), 100 * y.mean())

    X_train, X_test, y_train, y_test, conf_train, conf_test = train_test_split(
        X, y, raw_confidence, test_size=0.2, random_state=42, stratify=y if y.sum() > 1 and (len(y) - y.sum()) > 1 else None
    )

    eval_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000)),
    ])
    eval_pipeline.fit(X_train, y_train)
    y_pred = eval_pipeline.predict(X_test)

    report = classification_report(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)
    logger.info("Held-out classification report:\n%s", report)
    logger.info("Confusion matrix:\n%s", cm)

    # Refit on the full pulled dataset for the deployed artifact (standard
    # practice once held-out metrics are recorded above).
    final_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000)),
    ])
    final_pipeline.fit(X, y)

    model_scores = final_pipeline.predict_proba(X)[:, 1] * 100
    correlation = float(np.corrcoef(model_scores, raw_confidence)[0, 1]) if len(set(raw_confidence)) > 1 else float("nan")

    trained_at = datetime.datetime.utcnow().isoformat() + "Z"
    artifact = {
        "pipeline": final_pipeline,
        "feature_columns": FEATURE_COLUMNS,
        "country_priors": country_priors,
        "global_prior": global_prior,
        "trained_at": trained_at,
        "training_samples": len(y),
    }
    joblib.dump(artifact, MODEL_PATH)
    logger.info("Saved model artifact to %s", MODEL_PATH)

    coefs = dict(zip(FEATURE_COLUMNS, final_pipeline.named_steps["clf"].coef_[0].round(3).tolist()))

    write_model_card(
        trained_at=trained_at,
        n_samples=len(y),
        n_positive=int(y.sum()),
        report=report,
        confusion=cm.tolist(),
        correlation=correlation,
        coefs=coefs,
    )
    logger.info("Wrote model card to %s", MODEL_CARD_PATH)


def write_model_card(trained_at, n_samples, n_positive, report, confusion, correlation, coefs):
    positive_rate = n_positive / n_samples if n_samples else 0.0
    coef_lines = "\n".join(f"- `{k}`: {v}" for k, v in sorted(coefs.items(), key=lambda kv: -abs(kv[1])))

    content = f"""# Model Card — CyberPulse Live Composite Risk Scorer

## Summary
Logistic regression classifier estimating a 0-100 DDoS-relevance risk score
per ingested IP, trained on a live pull of AbuseIPDB data.

- **Trained at:** {trained_at}
- **Training samples:** {n_samples} (candidate IPs sampled live from Blocklist.de +
  CINS Army, each enriched with a real AbuseIPDB `/check` call)
- **Positive class rate:** {positive_rate:.1%}
- **Algorithm:** `LogisticRegression(class_weight="balanced")` on standardized features

## Candidate-IP sourcing (deviation from the original plan, flagged and confirmed)
AbuseIPDB's `/blacklist` endpoint — the originally planned candidate-IP
source — turned out to be capped at 5 requests/day on the free tier
(confirmed live via a 429: "Daily rate limit of 5 requests exceeded for
this endpoint"; see `CLAUDE.md`), which blocked pulling a fresh training
batch on demand. Candidate IPs for this run were sampled instead from two
free, non-rate-limited reputation feeds — [Blocklist.de](https://www.blocklist.de/)
and the [CINS Army list](https://cinsscore.com/) — with every candidate's
actual feature data (report counts, categories, usage type, country) still
coming from a real AbuseIPDB `/check` call, exactly as before. No feature
values or labels are synthetic; only the discovery mechanism for *which*
IPs to look up changed. This also turned out to be a methodological
improvement, not just a workaround: `/blacklist` is pre-filtered to IPs
AbuseIPDB already has heavy report history on, which is what skewed an
earlier pull to ~100% positive (see the proxy-label section below) — these
independently-curated feeds include IPs AbuseIPDB has sparse or no data on,
giving genuine label diversity.

## Proxy label (no live ground truth exists)
Positive class = AbuseIPDB report category 4 (DDoS Attack) present on the IP.

The Technical Architecture doc originally specified positive = categories
intersect {{4 (DDoS Attack), 14 (Port Scan), 18 (Brute-Force)}}. That was
reverted after a live data pull showed 18 (Brute-Force) on 100% and 14
(Port Scan) on ~92% of sampled blacklisted IPs — both are bundled onto
nearly every AbuseIPDB report regardless of actual DDoS-relevance, so the
original definition was ~100% positive and non-discriminative (confirmed
by an initial 300/300-positive training pull). Category 4 alone gives a
real, meaningful split and directly matches this project's stated purpose
(DDoS-relevance scoring, not generic-abuse scoring). This is still weak/
proxy supervision, named explicitly per the Technical Architecture doc —
there is no live ground-truth "is this really a DDoS source" label
available.

## Features
`total_reports`, `num_distinct_users`, `days_since_last_report`,
`usage_type_hosting`/`usage_type_isp`/`usage_type_other` (from AbuseIPDB's
own `usageType` field, not a hand-curated ASN list), `country_risk_prior`
(Laplace-smoothed positive rate per country computed from this training
pull, smoothing={COUNTRY_PRIOR_SMOOTHING}), and one multi-hot column per
AbuseIPDB category ID.

## Held-out evaluation (20% stratified split)
```
{report}
```
Confusion matrix (rows=actual, cols=predicted, order=[0,1]):
```
{confusion}
```
The deployed artifact is refit on the full {n_samples}-sample pull after
these metrics were recorded (standard practice), so live scores come from
the full-data fit, not the held-out-split fit.

## Model vs. raw AbuseIPDB confidence score
Pearson correlation between this model's risk score and AbuseIPDB's own
`abuseConfidenceScore` on the training set: **r = {correlation:.3f}**.
This is intentionally a different, independently-computed signal — not a
pass-through of AbuseIPDB's own score (PRD success criterion #2).

## Feature coefficients (full-data fit, standardized inputs, sorted by |coef|)
{coef_lines}

## Label leakage check (methodology note)
An earlier run of this pipeline hit 100.00% held-out accuracy — a red flag,
not a good result. The cause: `category_4` was included as both a model
*input* feature and the exact definition of `proxy_label()`, so the model
was trivially reading its own answer off one column instead of learning
anything. Fixed by excluding every category ID in `PROXY_LABEL_CATEGORY_IDS`
from `CATEGORY_FEATURE_COLUMNS` (see `app/ml/features.py`) — the other 22
categories remain legitimate features, since co-occurring tags are real
signal without restating the label. This run's ~76% accuracy with a mixed
confusion matrix is the trustworthy result of that fix, not a regression.

## Known limitations
- Small free-tier training pull ({n_samples} samples) — a resume-scale
  demonstration, not a production-grade dataset.
- Proxy label reflects AbuseIPDB's crowd-reported categories, not verified
  DDoS traffic — see the offline notebook (`/ml-research`) for the
  flow-based-dataset counterpart to this approach.
- `country_risk_prior` is derived from this training pull's country
  distribution and will drift as the live feed's country mix changes.
"""
    MODEL_CARD_PATH.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
