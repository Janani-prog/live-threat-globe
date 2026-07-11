# Product Requirements Document (PRD)
## Project: CyberPulse — Live DDoS Threat Intelligence Globe

### 1. Summary
CyberPulse is a full-stack, ML-augmented web application that visualizes DDoS-related threat activity on an interactive 3D globe in near-real time. It periodically ingests public threat-intelligence feeds, geolocates attacker IPs, scores them with a custom-trained ML model, and streams the results to a browser client that renders them as animated arcs and pulses on a globe, alongside a live stats dashboard.

This is a portfolio/resume project. Every design decision below optimizes for: (a) technical depth an interviewer can probe, (b) honesty about what the system actually does (no inflated claims), (c) zero ongoing cost, (d) buildability by an AI coding agent (Claude Code) working from this doc set.

### 2. Problem / Motivation
Threat intelligence dashboards (Kaspersky Cyberthreat Map, Digital Attack Map, etc.) are visually compelling but are closed-source black boxes. This project reproduces the core idea — transparently, end-to-end, with a documented and defensible ML component — as a demonstration of:
- Real-time-feeling data pipelines (polling + WebSocket push)
- Applied ML on security telemetry (feature engineering, offline training, live inference)
- Geospatial data visualization
- Pragmatic full-stack architecture under real free-tier constraints

### 3. Explicit Non-Goals (say this in interviews — it's a strength, not a weakness)
- **Not a packet-level sniffer.** We do not capture raw network traffic. We consume public, already-aggregated/reported threat intel (AbuseIPDB reports, Cloudflare Radar aggregates).
- **Not literally "every attack on Earth."** The feed is a periodically polled, rate-limited sample — presented as a live-feeling stream, same technique real vendor maps use.
- **Not a security product.** No claim of production-grade attack detection or mitigation. It is an educational/demonstration visualization.
- **Not multi-tenant / user-accounts based.** Public, read-only dashboard. No login required for v1.

### 4. Target Users
1. **Primary:** You, presenting this in interviews and on a portfolio site/GitHub README.
2. **Secondary:** Any visitor to the deployed link who wants to explore live-ish DDoS-related IP activity.

### 5. Core Features (v1 / MVP)

| # | Feature | Description |
|---|---|---|
| F1 | Live ingestion pipeline | Periodic background job polls AbuseIPDB blacklist + Cloudflare Radar attack-layer trends |
| F2 | Geolocation | Resolve attacker IPs to lat/long + country/ASN via free geolocation API, with caching |
| F3 | ML Risk Scoring (live) | Custom-trained composite classifier scores each ingested IP with a DDoS-relevance risk score (0–100), independent of AbuseIPDB's own score |
| F4 | Real-time push | WebSocket channel streams new/updated threat events to connected clients as they're ingested |
| F5 | 3D Globe visualization | Animated globe renders attacker→approximate-target arcs, pulsing markers sized/colored by risk score |
| F6 | Live stats dashboard | Rolling counters: total events, top attacking countries, top ASNs, attack category breakdown, requests/min trend chart |
| F7 | Event detail panel | Click a marker/arc → side panel with IP (partially masked for privacy-consciousness), country, ASN, category, risk score, contributing report count |
| F8 | Offline ML showcase | A separate Jupyter notebook (not called at runtime) training a classifier on a public labeled DDoS flow dataset (CICDDoS2019), with metrics/confusion matrix — linked from the README as "how I validated the ML approach further" |

### 6. Stretch Features (v2, only after MVP is solid)
- S1: Historical playback (scrub back through the last N hours of ingested events, stored in SQLite)
- S2: Simple config/admin view (adjust poll interval, feed toggles) — protected by a single shared secret, not full auth
- S3: Country-level choropleth overlay using Cloudflare Radar's aggregate attack-share data
- S4: Export current snapshot as JSON/CSV

### 7. Data Sources (free tier, verify limits before build)
- **AbuseIPDB** — free tier: blacklist endpoint (reported malicious IPs + confidence score + category codes), ~1,000 checks/day if also doing individual lookups. Requires free API key.
- **Cloudflare Radar API** — free, aggregated attack-layer (L3/L7) trend data by country/ASN. No per-IP data (by design/privacy) — used for the stats dashboard trend charts, not the globe markers.
- **Geolocation** — ip-api.com (free, ~45 req/min, no key) or ipinfo.io (free tier, 50k/month, requires key). Cache aggressively; never re-geolocate an IP seen in the last 24h.
- All API keys are configuration, not code — see Security & Access doc.

### 8. Success Criteria
- Globe updates visibly within the poll interval (target: every 10–30s) without manual refresh.
- ML risk score is demonstrably different from a naive pass-through of AbuseIPDB's own confidence score (documented with a short comparison in the README).
- Entire stack runs on a single free hosting instance with $0 recurring cost.
- A stranger can read the README in under 5 minutes and understand exactly what is real-time, what is polled, and what the ML model does and doesn't do.

### 9. Out of Scope Risks to Flag to Interviewers Proactively
- Free-tier API rate limits mean the "live" feed has gaps under heavy polling — documented, not hidden.
- Free hosting (Render/Fly free web service) may cold-start after idle — documented as a known trade-off, with a mitigation note (e.g., a lightweight keep-alive ping, optional).

### 10. Deliverable Definition of Done
A publicly reachable URL, a GitHub repo with clean commit history following the phased ticket list, a README with architecture diagram + demo GIF, and the offline ML notebook committed alongside the app. The frontend design and layout must perfectly match the specifications pulled dynamically from the connected Google Stitch MCP server.
