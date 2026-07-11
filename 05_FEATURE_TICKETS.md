# Feature Ticket List / Execution Phases
## Project: CyberPulse

Each phase should be completed, tested, and committed before the next begins. Claude Code should run each phase as a distinct session/prompt referencing this file plus the relevant spec doc(s). Do not skip ahead to frontend polish before the ingestion pipeline is proven to actually produce real events end-to-end — a beautiful globe with fake/static data is not the resume story we want.

---

### Phase 0 — Repo Scaffolding & Environment
- [ ] Initialize monorepo structure: `/backend`, `/frontend`, `/ml-research`, root `README.md`, root `.gitignore` (must exclude `.env`, `__pycache__`, `node_modules`, `*.db`, `venv`)
- [ ] Backend: FastAPI project skeleton, `requirements.txt` with pinned versions, `.env.example`
- [ ] Frontend: Vite + React + Tailwind scaffold, `.env.example` if any frontend-side config needed (e.g. WS URL for local dev)
- [ ] `CLAUDE.md` in repo root (see accompanying file) committed so future sessions have persistent context
- [ ] Verify: backend runs locally with `uvicorn app.main:app --reload`, returns 200 on `/health`; frontend runs with `npm run dev` and renders a placeholder page
- **Definition of done:** clean `git log` showing this as commit 1, both halves run locally, nothing secret committed

### Phase 1 — Data Ingestion Pipeline
- [ ] Implement `app/ingestion/abuseipdb.py`: fetch blacklist endpoint, parse into normalized internal event schema, handle auth via env var API key, handle 429/error responses gracefully
- [ ] Implement `app/ingestion/cloudflare_radar.py`: fetch aggregate attack-trend data, normalized separately (feeds stats endpoints, not per-IP events)
- [ ] Implement `app/geo/` geolocation client + SQLite-backed cache (check cache before calling external API; TTL/last-seen logic)
- [ ] Implement SQLite models/schema (`events`, `geo_cache`) per Technical Architecture doc
- [ ] Implement `app/scheduler.py`: APScheduler job wired into FastAPI lifespan, running the full ingest→geolocate→persist cycle on an interval (make interval configurable via env var, with a hard-coded safe minimum)
- [ ] Write a small script or test that runs one ingestion cycle manually and prints what got stored — verify against real API responses, not mocks, at least once
- **Definition of done:** running the backend for a few minutes populates real rows in SQLite with real geolocated coordinates, without manual intervention

### Phase 2 — ML: Live Composite Risk Scorer
- [ ] Pull a historical batch of AbuseIPDB data (larger sample than a live poll) to use as a training set
- [ ] Build `app/ml/features.py`: feature engineering per Technical Architecture doc section 5a (report count, distinct reporters, recency, category one-hot, ASN type)
- [ ] Construct the proxy label from AbuseIPDB category codes (document the exact mapping used — this is the part to be ready to explain in an interview)
- [ ] Train a logistic regression baseline in a notebook/script under `/backend/app/ml/training/`, evaluate with a held-out split (precision/recall, not just accuracy — class imbalance is likely)
- [ ] Export trained model artifact (`model.pkl` + a small `model_card.md` describing features, training date, metrics) into `app/ml/`
- [ ] Implement `app/ml/scorer.py`: loads the artifact once at startup, exposes `score(features) -> risk_score`
- [ ] Wire scorer into the ingestion cycle from Phase 1 — every newly seen IP gets a `risk_score` persisted alongside its event row
- [ ] Add a short comparison note (script output or notebook cell) showing the model's risk score vs. AbuseIPDB's raw confidence score are not identical/perfectly correlated — this backs PRD success criterion #2
- **Definition of done:** live events in SQLite have a populated, model-derived `risk_score` column; `model_card.md` exists and is accurate

### Phase 3 — Backend API & Real-Time Push
- [ ] Implement REST routes: `GET /events/recent` (paginated, recent N events), `GET /stats/summary`, `GET /stats/timeseries`, `GET /health`
- [ ] Implement WebSocket route `/ws/events`: connection manager, broadcast newly ingested events (hook into the end of the Phase 1 ingestion cycle)
- [ ] Apply Security & Access doc controls: rate limiting on REST routes, CORS restricted appropriately for local dev vs. prod config, IP hashing before anything touches an API response, WebSocket per-IP connection cap
- [ ] Basic automated tests: at least one test per route (can use FastAPI's `TestClient`), one test for the WebSocket broadcast path
- **Definition of done:** `curl`/Postman against every REST route returns sensible data; a simple WebSocket test client receives broadcast events live during an ingestion cycle

### Phase 4 — Frontend: Globe & Real-Time Feed
- [ ] Query the connected Stitch MCP server to retrieve the exact styling, geometry, and layout constraints for the 3D Globe and Event Detail Panel.
- [ ] Implement `ThreatFeedContext`: WebSocket connection + reconnect/backoff logic + ring buffer, initial hydration from `/events/recent`.
- [ ] Implement `<GlobeView>` and `<EventDetailPanel>` strictly adhering to the Stitch design context, wiring them to the `ThreatFeedContext`.
- **Definition of done:** The UI matches the dark, neon-terminal aesthetic from Stitch, and real events appear on the globe.

### Phase 5 — Frontend: Stats Dashboard & Polish
- [ ] Query the connected Stitch MCP server to retrieve the design specs for the top navigation bar, right-side toolbar, and bottom legend strip.
- [ ] Implement the stat strip and charts, adhering strictly to the Stitch constraints (no rounded corners, monospace fonts only, specific color palette).
- [ ] Wire the components to the `/stats/summary` and `/stats/timeseries` backend REST endpoints.
- **Definition of done:** The app functions correctly with live data and looks like a polished, raw security appliance matching the Stitch MCP blueprint exactly.

### Phase 6 — Offline ML Showcase Notebook
- [ ] Acquire CICDDoS2019 (or equivalent public labeled DDoS flow dataset) — document licensing/citation properly in the notebook
- [ ] EDA + feature selection, train Random Forest or XGBoost classifier on flow features
- [ ] Evaluate: confusion matrix, precision/recall/F1 per attack class, feature importance plot
- [ ] Write narrative markdown cells connecting this notebook back to the live system's design choice (section 5b of Technical Architecture) — this connective tissue is what makes it a coherent story instead of two unrelated projects bolted together
- **Definition of done:** notebook runs top-to-bottom without errors on a fresh environment, is linked from the root README

### Phase 7 — Deployment
- [ ] Write single `Dockerfile` (multi-stage: build frontend, install backend deps, copy built frontend into FastAPI's static directory) per Technical Architecture doc section 7
- [ ] Configure Render (or Fly.io) free web service, set all environment variables via the dashboard (never committed)
- [ ] Verify `.gitignore` one more time before this step — a deploy is exactly when a stray committed `.env` gets noticed by someone else
- [ ] Smoke test the deployed URL: globe loads, WebSocket connects (check for mixed-content/WSS issues — deployed HTTPS requires `wss://`, not `ws://`), ingestion cycle runs on the live instance
- [ ] Document the cold-start trade-off in the README; optionally wire up a free uptime pinger if desired
- **Definition of done:** a public URL that a stranger can open cold and see a working, updating dashboard within a reasonable wait

### Phase 8 — README, Repo Polish & Resume Framing
- [ ] Root `README.md`: problem statement, architecture diagram (can reuse/adapt the ASCII diagram from the Technical Architecture doc, or render it properly), setup instructions, live demo link, explicit "what's real-time vs. polled, what the ML model does and doesn't do" section (ties back to PRD non-goals — this is the section that makes the project credible in an interview)
- [ ] Demo GIF/screen recording embedded in the README
- [ ] Link to the offline ML notebook from the README
- [ ] Final pass: remove dead code, unused deps, TODO comments; confirm `pip-audit`/`npm audit` come back clean or with documented exceptions
- **Definition of done:** the repo is something you'd be comfortable linking directly in a resume/LinkedIn without further cleanup

---

### Stretch Phases (only after Phase 8 is fully done)
- **Phase 9 — Historical playback** (PRD stretch S1)
- **Phase 10 — Admin config panel** (PRD stretch S2, shared-secret protected per Security doc section 8)
- **Phase 11 — Country choropleth overlay** (PRD stretch S3)
