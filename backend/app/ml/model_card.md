# Model Card — CyberPulse Live Composite Risk Scorer

## Summary
Logistic regression classifier estimating a 0-100 DDoS-relevance risk score
per ingested IP, trained on a live pull of AbuseIPDB data.

- **Trained at:** 2026-07-11T10:37:10.720069Z
- **Training samples:** 249 (candidate IPs sampled live from Blocklist.de +
  CINS Army, each enriched with a real AbuseIPDB `/check` call)
- **Positive class rate:** 43.0%
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
intersect {4 (DDoS Attack), 14 (Port Scan), 18 (Brute-Force)}. That was
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
pull, smoothing=5.0), and one multi-hot column per
AbuseIPDB category ID.

## Held-out evaluation (20% stratified split)
```
              precision    recall  f1-score   support

           0       0.81      0.76      0.79        29
           1       0.70      0.76      0.73        21

    accuracy                           0.76        50
   macro avg       0.76      0.76      0.76        50
weighted avg       0.76      0.76      0.76        50

```
Confusion matrix (rows=actual, cols=predicted, order=[0,1]):
```
[[22, 7], [5, 16]]
```
The deployed artifact is refit on the full 249-sample pull after
these metrics were recorded (standard practice), so live scores come from
the full-data fit, not the held-out-split fit.

## Model vs. raw AbuseIPDB confidence score
Pearson correlation between this model's risk score and AbuseIPDB's own
`abuseConfidenceScore` on the training set: **r = -0.169**.
This is intentionally a different, independently-computed signal — not a
pass-through of AbuseIPDB's own score (PRD success criterion #2).

## Feature coefficients (full-data fit, standardized inputs, sorted by |coef|)
- `country_risk_prior`: 1.719
- `category_6`: 1.161
- `category_14`: -0.843
- `category_21`: -0.677
- `category_11`: 0.649
- `category_23`: 0.61
- `category_18`: 0.606
- `category_8`: -0.57
- `category_5`: 0.469
- `num_distinct_users`: 0.446
- `category_7`: -0.431
- `category_20`: 0.416
- `category_9`: -0.409
- `days_since_last_report`: -0.377
- `total_reports`: -0.376
- `category_10`: 0.325
- `category_22`: -0.307
- `category_15`: 0.241
- `category_17`: -0.139
- `category_16`: 0.124
- `usage_type_other`: 0.074
- `usage_type_hosting`: -0.073
- `category_19`: 0.041
- `usage_type_isp`: 0.029
- `category_1`: 0.0
- `category_2`: 0.0
- `category_3`: 0.0
- `category_12`: 0.0
- `category_13`: 0.0

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
- Small free-tier training pull (249 samples) — a resume-scale
  demonstration, not a production-grade dataset.
- Proxy label reflects AbuseIPDB's crowd-reported categories, not verified
  DDoS traffic — see the offline notebook (`/ml-research`) for the
  flow-based-dataset counterpart to this approach.
- `country_risk_prior` is derived from this training pull's country
  distribution and will drift as the live feed's country mix changes.
