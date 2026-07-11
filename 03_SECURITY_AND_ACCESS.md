# Security & Access Document
## Project: CyberPulse

### 1. Threat Model Summary
This is a public, read-only, unauthenticated demo application with no user accounts and no sensitive user data. The realistic risks are: (a) leaking your own third-party API keys, (b) your own public API being abused/scraped/DDoS'd (ironic, but real), (c) displaying raw IPs in a way that's needlessly identifying, (d) supply-chain risk from dependencies.

### 2. Secrets Management
- **Never commit API keys.** AbuseIPDB key, Cloudflare Radar token/API key, and (if used) ipinfo.io key are all environment variables only.
- Local dev: `.env` file, listed in `.gitignore` from the very first commit (verify this before the first `git add`).
- Production: set via the hosting provider's environment variable dashboard (Render/Fly), never baked into the Docker image.
- Provide a committed `.env.example` with variable names but no values, so Claude Code (and future-you) knows exactly what's required to run the project.
- No secret should ever appear in logs. Review log statements in the ingestion clients specifically — API client libraries sometimes log full request URLs including query-string keys; use header-based auth where the provider supports it, and scrub logs otherwise.
- **Stitch MCP API Key:** The key used to connect Claude Code to the Stitch workspace is a local development secret. It must be managed via Claude's internal MCP configuration and never committed to a `.env` file or source control.

### 3. IP Handling / Privacy Posture
- Store a salted hash of ingested IPs (`ip_hash = sha256(ip + server_side_salt)`), not raw IPs, in any table reachable by a public API endpoint. The salt itself is an environment variable, not in source control.
- Raw IP is only needed transiently, in-memory, during the geolocation + risk-scoring step of the ingestion cycle — do not persist it beyond that cycle unless there's a specific, documented reason (there shouldn't be one for v1).
- Rationale to state in the README: these IPs are already publicly reported as abusive by AbuseIPDB's community, so this isn't protecting attacker privacy — it's a defensive practice against accidentally building an incidental "who reported/was-reported" dataset that a scraper of *your* API could harvest and correlate. Good practice regardless of the exact justification.
- No raw IP should ever be sent to the frontend. Frontend receives `ip_hash` (for React `key` uniqueness) plus country/ASN/category/score — everything needed for the visualization, nothing needed for re-identification.

### 4. API Surface Hardening
- **Rate limit your own public endpoints** (e.g. `slowapi`, a FastAPI-compatible rate limiter) — both to protect your free-tier hosting from being hammered, and because an uncapped public endpoint that fans out to a WebSocket broadcast is a self-inflicted amplification risk.
- **CORS**: restrict `allow_origins` to your actual deployed frontend origin in production; wildcard `*` is fine only in local dev, and Claude Code should not leave a wildcard in the production config.
- **Input validation**: all REST route parameters (pagination, filters) validated via Pydantic models — reject malformed input with a 422, don't let it reach the DB layer.
- **No stack traces to clients**: FastAPI's default exception responses should be overridden in production mode to return a generic error body; keep full tracebacks in server-side logs only.
- **WebSocket**: cap concurrent connections per IP address (simple in-memory counter) to prevent a single client from exhausting connection slots on a free-tier instance.

### 5. Third-Party API Usage Discipline
- Respect published rate limits for AbuseIPDB and Cloudflare Radar explicitly in code (a configurable poll interval + a hard-coded minimum floor so a misconfigured `.env` can't accidentally hammer their API and get your key banned).
- Handle 429s from upstream providers gracefully: exponential backoff, don't crash the scheduler loop, log and continue.
- Cache geolocation results — this is a rate-limit-protection measure as much as a performance one.

### 6. Dependency & Supply Chain Hygiene
- Pin dependency versions in `requirements.txt` / `package-lock.json` (don't use unpinned `*`).
- Run `pip-audit` (Python) and `npm audit` (frontend) as a step in the build process or a documented pre-deploy checklist — flag, don't necessarily block, given this is a portfolio project not a production system, but the discipline itself is the resume-worthy part.
- Avoid pulling in a large unmaintained globe/three.js wrapper if a well-maintained alternative exists — `react-globe.gl` is actively maintained as of this writing; Claude Code should verify current maintenance status before locking it in.

### 7. What This Project Deliberately Does NOT Need (and why, so no one over-engineers it)
- **User authentication**: no user accounts exist. Skip OAuth/JWT entirely for v1.
- **HTTPS termination in app code**: handled by the hosting provider (Render/Fly both terminate TLS at the edge) — don't build custom TLS handling.
- **A WAF or bot-management layer**: out of scope/cost for a portfolio project; rate limiting is the proportionate control here.
- **Encryption at rest for SQLite**: the data stored (hashed IPs, public threat categories, geolocation) is not sensitive enough to justify the added complexity for v1. State this reasoning explicitly if asked in an interview — knowing when *not* to add a control is as valuable as knowing when to add one.

### 8. Optional Admin Surface (only if Stretch Feature S2 is built)
- Protect with a single shared-secret header (e.g. `X-Admin-Token`), compared using a constant-time comparison, stored as an environment variable — not a full auth system, proportionate to a single-operator demo tool.
- Never expose this surface at a guessable path if it can be avoided (obscurity is not a substitute for the token check, but there's no reason to make it easy to find either).
