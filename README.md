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

## Status
See "Current phase" in [`CLAUDE.md`](CLAUDE.md) for where the build currently stands.
