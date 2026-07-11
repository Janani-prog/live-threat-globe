# CyberPulse

A live DDoS threat-intel visualization globe. Ingests public threat-intelligence feeds
(AbuseIPDB, Cloudflare Radar), geolocates and ML-scores reported IPs, and streams the
results to a browser client rendered as an animated 3D globe with a live stats dashboard.

Full project spec lives in the root-level docs:
- [`01_PRD.md`](01_PRD.md) — what this is and why, including explicit non-goals
- [`02_TECHNICAL_ARCHITECTURE.md`](02_TECHNICAL_ARCHITECTURE.md) — stack and architecture
- [`03_SECURITY_AND_ACCESS.md`](03_SECURITY_AND_ACCESS.md) — required security practices
- [`05_FEATURE_TICKETS.md`](05_FEATURE_TICKETS.md) — phased execution plan

## Repo layout
- `backend/` — FastAPI app: ingestion pipeline, ML scorer, REST + WebSocket API
- `frontend/` — Vite + React + Tailwind client: globe visualization + stats dashboard
- `ml-research/` — offline Jupyter notebook showcasing a classifier trained on a labeled DDoS dataset (not a runtime dependency)

## Local development

### Backend
```
cd backend
python -m venv venv
./venv/Scripts/activate   # or source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env      # fill in API keys, see 03_SECURITY_AND_ACCESS.md
uvicorn app.main:app --reload
```
Visit `http://localhost:8000/health`.

### Frontend
```
cd frontend
npm install
cp .env.example .env
npm run dev
```
Visit `http://localhost:5173`.

### Offline ML notebook
[`ml-research/offline_ddos_classifier.ipynb`](ml-research/offline_ddos_classifier.ipynb) —
trains a Random Forest classifier on NSL-KDD (a labeled, flow-based intrusion-detection
benchmark) to classify network traffic as benign vs. DoS/probe/R2L/U2R, and explains why the
*live* system's risk scorer uses a different, simpler feature set (it has no packet/flow-level
access — only AbuseIPDB's aggregated report metadata). Runs top-to-bottom on a fresh
environment; downloads its own ~7MB of data on first run.
```
cd ml-research
python -m venv venv
./venv/Scripts/activate
pip install -r requirements.txt
jupyter notebook offline_ddos_classifier.ipynb
```

## Deployment

Single `Dockerfile` at the repo root, multi-stage: builds the frontend, then copies the built
assets into the FastAPI backend's `static/` directory, which is served alongside the REST/
WebSocket API from the same origin (Technical Architecture doc section 7 — one service, one
process). Because everything is same-origin in production, the frontend doesn't need a
build-time API URL baked in — it falls back to relative/`window.location`-derived URLs when
`VITE_API_BASE_URL`/`VITE_WS_URL` aren't set (see `frontend/src/lib/apiConfig.ts`), which also
automatically resolves the WebSocket to `wss://` on an `https://` page (no mixed-content
issues).

### Build & run locally
```
docker build -t cyberpulse .
docker run -p 8000:8000 \
  -e IP_HASH_SALT=<generate a long random string> \
  -e ABUSEIPDB_API_KEY=<your key> \
  -e CLOUDFLARE_RADAR_API_TOKEN=<your token> \
  cyberpulse
```
Visit `http://localhost:8000` — same container serves the UI, REST API, and WebSocket.
Verified locally: `/health`, `/events/recent`, static asset serving, and a raw WebSocket
upgrade handshake to `/ws/events` all confirmed working from inside the built image.

### Deploy to Render (free tier)
1. Push this repo to GitHub.
2. In the Render dashboard: **New +** → **Blueprint**, connect the repo. Render reads
   [`render.yaml`](render.yaml) and provisions a Docker web service automatically.
3. Render will prompt for the env vars marked `sync: false` in `render.yaml`
   (`ABUSEIPDB_API_KEY`, `CLOUDFLARE_RADAR_API_TOKEN`, `IPINFO_API_KEY`, `IP_HASH_SALT`,
   `CORS_ALLOWED_ORIGINS`) — fill these in the dashboard, never in a committed file. Once
   Render assigns your service's URL, set `CORS_ALLOWED_ORIGINS` to that exact URL.
4. This step requires your own Render account/credentials, so it isn't something that can be
   done from here — the Dockerfile and blueprint are ready to go, connecting the repo and
   filling in secrets is a dashboard action for you to do.

### Known trade-offs (documented, not hidden — per the PRD's non-goals)
- **Ephemeral filesystem on Render's free tier.** Confirmed against Render's docs: free web
  services have no persistent disk (that's a paid-tier feature) — every redeploy, restart, or
  spin-down wipes the local SQLite file. In practice this means the ingested-event history
  resets periodically; the app already re-ingests from scratch on startup (`init_db()` +
  the scheduler's first poll), so it self-heals rather than erroring, but it's not a durable
  history store on the free tier.
- **Cold starts.** Render's free web services spin down after a period of inactivity and take
  some time to wake on the next request. A stranger opening a cold link may see a brief delay
  before the app responds. An optional free external pinger (e.g. UptimeRobot) hitting `/health`
  periodically can keep the instance warm if continuous responsiveness matters for a demo —
  not set up here, since it's opt-in and has its own trade-offs (counts against free-tier usage
  hours).
- **`/blacklist`'s 5-requests/day quota** (see `CLAUDE.md`) means a freshly-restarted instance
  (which just lost its event history to the ephemeral filesystem) may need to wait for its next
  scheduled `/blacklist` pull to repopulate the globe, rather than doing so instantly — the
  in-memory backlog from before the restart is also gone. This compounds with the ephemeral
  filesystem trade-off above.

## Status
See "Current phase" in [`CLAUDE.md`](CLAUDE.md) for where the build currently stands.
