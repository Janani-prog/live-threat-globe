# Real-Time Threat Intelligence Globe

A full-stack security visualization platform that ingests public DDoS and malicious-IP threat
feeds, enriches and scores each report with a trained machine learning model, and streams the
results to an interactive 3D globe over WebSockets — alongside a live statistics dashboard for
country, ASN, and attack-category breakdowns.

**Live demo:** [cyberpulse-hj9l.onrender.com](https://cyberpulse-hj9l.onrender.com/)
*(free-tier hosting — see [Operating at Free-Tier Scale](#operating-at-free-tier-scale) for the
cold-start and data-freshness trade-offs that come with that, stated up front rather than left
as a surprise.)*

![Demo](docs/demo.gif)

## Why This Exists

Security operations teams and threat researchers rely on situational-awareness tooling to
understand *where* attack traffic is originating, *what kind* of activity is being reported,
and *how* that risk should be prioritized. Commercial threat maps (Kaspersky Cyberthreat Map,
Digital Attack Map) demonstrate the value of this kind of visualization but are closed-source —
there's no visibility into how a displayed "risk" is actually computed.

This project builds that same category of tool transparently, end to end:

- **Multi-source ingestion** — ingests and cross-references community-reported malicious IPs
  (AbuseIPDB) and aggregate DDoS attack-layer trends (Cloudflare Radar), with an automatic
  fallback to independent reputation feeds (Blocklist.de, CINS Army) when a source's rate limit
  is exhausted, so data collection keeps flowing rather than silently going quiet.
- **Applied machine learning** — a supervised classifier scores every ingested IP for
  DDoS-relevance in real time, trained and evaluated with the same rigor as a production ML
  pipeline: documented feature engineering, weak-supervision labeling, held-out evaluation, and
  a written model card (`backend/app/ml/model_card.md`).
- **Real-time delivery at low operational cost** — a single containerized service handles
  ingestion scheduling, REST/WebSocket APIs, and static hosting, deployed for $0/month on
  free-tier infrastructure, engineered around the real constraints that come with that (rate
  limits, ephemeral storage, cold starts) rather than ignoring them.

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                  Threat Intelligence Sources                   │
│                                                                │
│ AbuseIPDB /blacklist + /check   (malicious IP reports)         │
│ Blocklist.de + CINS Army        (fallback IP feed)             │
│ Cloudflare Radar                (aggregate attack trends)      │
│ ip-api.com                      (IP geolocation)               │
└────────────────────────────────────────────────────────────────┘

                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│           Ingestion & Scoring Pipeline (APScheduler)           │
│                                                                │
│ 1. Discover candidate IPs from the sources above               │
│ 2. Geolocate + enrich each IP with report metadata             │
│ 3. Score DDoS relevance with a trained ML model                │
│ 4. Persist to SQLite and broadcast over WebSocket              │
└────────────────────────────────────────────────────────────────┘

                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                       │
│                                                                │
│ REST API        /events, /stats, /health                       │
│ WebSocket hub    real-time event streaming to clients          │
│ Static hosting   serves the built React frontend               │
└────────────────────────────────────────────────────────────────┘

                                 │  WebSocket + REST
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                 Browser Client  (React + Vite)                 │
│                                                                │
│ 3D interactive globe          react-globe.gl                   │
│ Live event stream              WebSocket subscriber            │
│ Statistics dashboard          Recharts                         │
└────────────────────────────────────────────────────────────────┘
```

The entire backend and pre-built frontend run as **one Docker container** — no separate
database service, message broker, or frontend host. This keeps the deployment footprint small
while still exercising a real multi-stage build (Node → Vite build → Python runtime) and a
real same-origin REST/WebSocket/static-asset serving setup.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Python, FastAPI, Pydantic, SQLAlchemy |
| Real-time transport | Native WebSockets (FastAPI/Starlette), a connection manager with per-IP connection limits |
| Background processing | APScheduler (async, in-process job scheduling) |
| Data storage | SQLite (event history, geolocation cache, API quota tracking) |
| Machine learning | scikit-learn (logistic regression classifier), joblib for model persistence |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Visualization | react-globe.gl (WebGL 3D globe), Recharts (statistics dashboard) |
| Infrastructure | Docker (multi-stage build), deployed on Render |
| Rate limiting & hardening | slowapi request throttling, salted IP hashing, CORS enforcement, structured error handling |

## Core Features

- **Live 3D globe visualization** — attacker IPs render as color-coded, risk-weighted markers
  on an interactive globe, updating in real time as new reports are ingested.
- **ML-driven risk scoring** — every IP receives an independently computed 0–100 DDoS-relevance
  score from a trained classifier, distinct from any single source's raw confidence rating.
- **Real-time event streaming** — a WebSocket channel pushes newly processed events to every
  connected client the instant they're persisted, with automatic reconnect and backoff on the
  client side.
- **Live statistics dashboard** — rolling counters and charts for total events, top attacking
  countries, top ASNs, and attack-category breakdown, backed by REST endpoints.
- **Resilient multi-source ingestion** — automatically falls back to alternate threat feeds when
  a primary source's rate limit is exhausted, so the pipeline degrades gracefully instead of
  going dark.
- **Privacy-conscious data handling** — raw IP addresses are never persisted or exposed through
  the API; only a salted one-way hash is stored, alongside geolocation and category metadata.
- **Offline ML research notebook** — a companion Jupyter notebook (`ml-research/`) trains and
  evaluates a Random Forest classifier on a labeled, flow-based network intrusion dataset,
  documenting a second, independent approach to the same class of problem.

## How the System Behaves in Practice

Not every layer of this system updates at the same cadence, and that's worth stating plainly
rather than letting "real-time globe" imply something it isn't:

| Layer | Behavior |
|---|---|
| Browser ↔ backend event delivery | **Real-time.** Every newly processed event is pushed over WebSocket the instant it's written — no polling on the client for event data. |
| New-IP discovery | **Periodic (~every 6 hours), with automatic fallback.** Public threat-intel APIs impose strict rate limits on bulk discovery endpoints; the pipeline respects those limits and supplements with independent feeds when needed, rather than exceeding them. |
| Enrichment, scoring, and delivery | **Continuous (~30-second cycle).** Newly discovered IPs are drained from an internal queue, enriched, scored, and broadcast on a steady cadence — so the globe keeps animating between the less-frequent discovery cycles above. |
| Aggregate statistics dashboard | **Polled (~every 30 seconds).** Aggregate rollups don't need push delivery. |
| Geolocation | **Cached (24 hours per IP).** Avoids redundant lookups against rate-limited geolocation services. |

## Machine Learning Approach

**Live risk scorer** (`backend/app/ml/`) — a logistic regression classifier trained on
report metadata (report volume, distinct-reporter count, report recency, category tags, hosting
classification, and a per-country risk prior), producing a 0–100 DDoS-relevance score for each
IP at ingestion time. Because no verified ground-truth label exists for "this IP is definitively
a DDoS source," the model is trained against a documented weak-supervision proxy label — achieving
~76% held-out accuracy on a genuinely mixed confusion matrix (not memorization) — with the full
methodology, evaluation metrics, and known limitations recorded in `backend/app/ml/model_card.md`.
The resulting score correlates only weakly with any single source's own confidence rating
(r ≈ -0.17), confirming it as an independently computed signal rather than a relabeled
pass-through.

**Offline research notebook** (`ml-research/offline_ddos_classifier.ipynb`) — a Random Forest
classifier trained on a labeled, flow-based network intrusion benchmark (41 packet/flow-derived
features), evaluated with a confusion matrix, per-class precision/recall, and a feature
importance analysis. This notebook explores the class of problem this system is built around
using a richer feature set than the production pipeline has access to, and documents the
reasoning behind that architectural choice.

## Local Development

### Backend
```bash
cd backend
python -m venv venv
./venv/Scripts/activate   # or source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env      # populate with your own API keys
uvicorn app.main:app --reload
```
Visit `http://localhost:8000/health`.

### Frontend
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Visit `http://localhost:5173`.

### Offline ML Notebook
```bash
cd ml-research
python -m venv venv
./venv/Scripts/activate
pip install -r requirements.txt
jupyter notebook offline_ddos_classifier.ipynb
```
Runs top-to-bottom on a fresh environment and downloads its own dataset on first run.

## Deployment

A single multi-stage `Dockerfile` builds the frontend and packages it alongside the backend, so
the deployed container serves the REST API, WebSocket connections, and static frontend assets
from one process and one origin.

```bash
docker build -t threat-globe .
docker run -p 8000:8000 \
  -e IP_HASH_SALT=<a long random string> \
  -e ABUSEIPDB_API_KEY=<your key> \
  -e CLOUDFLARE_RADAR_API_TOKEN=<your token> \
  threat-globe
```

A [Render Blueprint](render.yaml) is included for one-click infrastructure provisioning —
connect the repository in Render's dashboard and the service, environment variable prompts, and
health checks are configured automatically.

## Operating at Free-Tier Scale

Every architectural trade-off below is a deliberate, cost-conscious engineering decision, not
an oversight — and each is handled with a graceful degradation path rather than a failure mode:

- **Ephemeral storage.** Free-tier hosting doesn't provide a persistent disk, so event history
  resets on redeploys or extended idle periods. The application detects this on startup and
  re-populates itself automatically — no manual intervention required.
- **Cold starts.** An idle free-tier instance spins down and takes a few moments to wake on the
  next request; this is a known and accepted trade-off of running at zero infrastructure cost.
- **Third-party rate limits.** External threat-intel APIs impose strict daily request caps on
  bulk-discovery endpoints. Rather than exceed them, the ingestion pipeline is explicitly
  quota-aware and automatically supplements with alternate data sources when a limit is reached.

## Security Practices

- Raw IP addresses are hashed with a server-side salt before persistence or API exposure —
  the raw address exists only transiently, in memory, during processing.
- All public endpoints are rate-limited to prevent abuse of the free-tier hosting quota.
- CORS is explicitly scoped to the deployed origin in production.
- No stack traces or internal error detail are ever returned to a client; all exceptions are
  logged server-side and surfaced to the client as a generic error response.
- Secrets are supplied exclusively via environment variables and are never committed to source
  control.

## Repository Layout

```
backend/       FastAPI application — ingestion pipeline, ML scoring, REST + WebSocket API
frontend/      React + Vite client — 3D globe visualization and statistics dashboard
ml-research/   Offline Jupyter notebook — a companion ML research artifact
```
