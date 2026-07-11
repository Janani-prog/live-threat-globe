# Technical Architecture Document
## Project: CyberPulse

### 1. Guiding Constraints
- **$0 recurring cost.** Every service used must have a genuinely free tier (not a trial).
- **Single deployable process.** One web service (Render or Fly.io free tier) serves the API, the WebSocket, the background ingestion scheduler, AND the built frontend static assets. No separate DB service, no separate Redis service, no separate frontend host.
- **Runs cold-start-safe.** Free-tier instances sleep on idle; on wake, the app must self-heal (re-warm cache, resume scheduler) without manual intervention.

### 2. High-Level Architecture

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

All four stages run inside a single Docker container (one process, one origin) — no separate
database service, message broker, or frontend host, per the guiding constraints above.

### 3. Backend (FastAPI)

**Why FastAPI:** async-native (needed for concurrent polling + WebSocket fan-out), automatic OpenAPI docs (nice for a resume link), Pydantic validation, minimal boilerplate.

**Core modules:**
- `app/main.py` — FastAPI app factory, lifespan hooks (start/stop scheduler on app startup/shutdown)
- `app/ingestion/` — one module per data source (`abuseipdb.py`, `cloudflare_radar.py`), each returning a normalized internal event schema
- `app/geo/` — geolocation client + SQLite-backed cache layer (IP → lat/long/country/ASN, with a TTL/last-seen column)
- `app/ml/` — `features.py` (feature engineering from raw event), `scorer.py` (loads the trained model artifact and returns a risk score), `model.pkl` (trained artifact, committed to repo — it's small)
- `app/realtime/` — WebSocket connection manager (broadcast to all connected clients); in-memory, since we're single-process (no Redis needed at this scale)
- `app/api/` — REST routes: `/events/recent`, `/stats/summary`, `/stats/timeseries`, `/health`
- `app/db/` — SQLite models (SQLAlchemy or raw `sqlite3` — recommend SQLAlchemy for clarity), migrations via Alembic (lightweight, or a simple `init_db()` for a project this size — Claude Code should judge based on how much schema churn is expected)
- `app/scheduler.py` — APScheduler job(s): poll AbuseIPDB every N seconds, poll Cloudflare Radar on a slower cadence (it's aggregate data, doesn't need to be as frequent), run geolocation + ML scoring on new IPs, persist, broadcast over WebSocket

**Background job flow (single cycle):**
1. Fetch AbuseIPDB blacklist (paginated, respecting free-tier limits)
2. Diff against already-seen IPs (avoid re-processing) — check geo cache first
3. For new/unseen IPs: geolocate (cache result), extract ML features, score with the trained model
4. Persist event row to SQLite
5. Broadcast the new event(s) to all connected WebSocket clients
6. Update rolling stats aggregates (top countries, categories, counts) — either recomputed on read or incrementally maintained; recommend incremental counters for a project this size, recomputed periodically as a sanity check

### 4. Data Layer

**Why SQLite, not Postgres:** Single-service constraint. Render/Fly free web services give you a small persistent (or ephemeral, depending on plan — verify) disk; SQLite is a single file, needs no separate managed DB service, and this project's write volume is trivially within SQLite's comfort zone. Document clearly in the README: "if scaling beyond a demo, swap to Postgres — schema is designed to be ORM-portable."

**Core tables:**
- `events(id, ip_hash, lat, lon, country, asn, category, confidence_source, risk_score, reported_at, ingested_at)`
- `geo_cache(ip_hash, lat, lon, country, asn, last_checked_at)`
- `stats_rollup(window_start, window_end, country, category, count)` (only if incremental aggregation is implemented)

**Privacy note:** store a salted hash of the raw IP (`ip_hash`), not the raw IP, in any table exposed via API — see Security & Access doc for rationale. Keep raw IP only transiently in-memory during the ingestion cycle if needed for geolocation lookups.

### 5. ML Component

**5a. Live composite risk scorer (used at runtime)**
- **Input features** (per IP, from AbuseIPDB + geo data): total report count, distinct reporter count, days since last report, category distribution (one-hot/multi-hot over AbuseIPDB category codes), ASN type (hosting/datacenter vs residential — inferable from ASN registry data or a small curated list), country risk prior (optional, computed from historical event volume).
- **Model:** start with logistic regression (interpretable, fast, easy to explain in an interview) or a small gradient-boosted tree (e.g. `xgboost` or `lightgbm`) if there's time — trade-off is explainability vs. marginal accuracy gain. Recommend starting with logistic regression; upgrade only if time allows.
- **Training data:** since there's no ground-truth "is this really a DDoS source" label available live, train against a proxy label constructed from AbuseIPDB category codes (e.g., categories tagged DDoS/port-scan/brute-force = positive proxy class) on a historical pull, explicitly documented as a proxy-label approach — this is a completely normal and defensible ML practice (weak/proxy supervision) and should be named as such in the README, not hidden.
- **Output:** a 0–100 risk score, stored per event, driving marker color/size on the globe. This is a different, model-derived number from AbuseIPDB's own confidence score — the PRD's success criterion #2 depends on this being genuinely computed, not copied.

**5b. Offline showcase notebook (not called at runtime)**
- Trains a classifier (Random Forest or XGBoost) on a public labeled flow-based dataset such as CICDDoS2019 (Canadian Institute for Cybersecurity) to classify network flows as benign vs. various DDoS attack types.
- Lives in `/ml-research/` in the repo as a Jupyter notebook with markdown narrative, feature importance plot, confusion matrix, and a short written conclusion connecting it back to why the live system uses proxy-labeled AbuseIPDB features instead of raw flow features (answer: we don't have live raw flow data — only aggregated/reported IP metadata — so this notebook demonstrates the "if we had packet-level access" version of the problem).
- This notebook is a resume artifact first, a runtime dependency never.

### 6. Frontend (React + Vite)
- **Stitch MCP Integration:** The entire UI layout, color palette (neon cyberpunk), monospace typography, and component geometry are managed in Google Stitch. Claude Code MUST query the connected Stitch MCP server to retrieve the exact design requirements before building any React components.
- **Globe:** Render arcs and point markers colored/sized by risk score as specified by the Stitch design.
- **Real-time:** A single WebSocket connection, reconnect-with-backoff logic, feeding new events into local state.
- **Build output:** static files built via `vite build`, served directly by FastAPI's `StaticFiles` mount.
- **Globe:** `react-globe.gl` (wraps three.js/globe.gl) — renders arcs (attacker → generic "observer" point, or just pulsing points if arcs feel gimmicky) and point markers colored/sized by risk score.
- **Real-time:** a single WebSocket connection, reconnect-with-backoff logic, feeding new events into local state (capped ring buffer, e.g. last 500 events, to avoid unbounded memory growth in a long-running browser tab).
- **Stats dashboard:** simple charts (Recharts) for top countries/categories/time series, backed by the REST `/stats/*` endpoints (polled every 30–60s, doesn't need WebSocket).

### 7. Deployment
- **Host:** Render (free Web Service) or Fly.io (free allowance) — pick one; Render is simpler to set up, Fly gives more control. Recommend Render for this project's scope.
- **Process:** one `Dockerfile` (or Render's native Python runtime) that: installs backend deps, builds the frontend (`npm ci && npm run build` in a build step or multi-stage Docker build), copies the built assets into the location FastAPI serves statically, then runs `uvicorn`.
- **Config:** all API keys and secrets via environment variables set in the Render dashboard — never committed. See Security & Access doc.
- **Cold start mitigation:** document the trade-off; optionally add a free external uptime pinger (e.g. UptimeRobot free tier) if truly continuous uptime matters for demos — this is optional and should be called out as such, not silently assumed.

### 8. Why these choices, briefly (for interview prep)
- FastAPI over Flask/Django: native async fits the polling + WebSocket pattern without bolting on extensions.
- SQLite over Postgres: matches the single-service, low-write-volume reality of this project; documented upgrade path shows awareness of when it wouldn't scale.
- Proxy-labeled logistic regression over an unsupervised anomaly detector: more interpretable, easier to defend in an interview, and matches the actual data available (categorical reports, not raw traffic).
- react-globe.gl over hand-rolled three.js: keeps frontend effort proportional to project scope — the value-add here is the pipeline + ML, not reinventing globe rendering.
