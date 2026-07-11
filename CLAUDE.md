# CLAUDE.md — Project Instructions for Claude Code

This file is auto-loaded by Claude Code at the start of every session in this repo. Read it before doing anything.

## What this project is
CyberPulse — a live DDoS threat-intel visualization globe. Full context lives in `/docs`:
- `01_PRD.md` — what we're building and why, including explicit non-goals
- `02_TECHNICAL_ARCHITECTURE.md` — the stack and how pieces fit together
- `03_SECURITY_AND_ACCESS.md` — required security practices, non-negotiable
- `05_FEATURE_TICKETS.md` — the phased execution plan; **work through phases in order**
## Frontend Constraints (CRITICAL)
- `Google Stitch MCP` — The baseline frontend UI/UX is available via the connected Stitch MCP server. You MUST query it to retrieve the core design system (colors, typography, and broad layout constraints). However, the Stitch design is a high-level conceptual blueprint. You have explicit permission to enhance, polish, and fill in UI gaps (e.g., hover states, micro-interactions, responsive adjustments, and empty states) to elevate the final product. Maintain the strict dark, neon-terminal aesthetic, but use your best judgment to build a complete, professional-grade interface.

## Operating instructions
1. **These docs are the spec, not a cage.** If you find a better approach than what's written — a cleaner library, a schema that'll save a migration later, a security control we missed — use your judgment and do it. Leave a short comment or commit message explaining the deviation and why, so the reasoning isn't lost. Don't silently deviate from something safety/privacy related (Security doc) without flagging it clearly in your response to me.
2. **Don't skip ahead.** Complete each phase's "Definition of done" before starting the next. If a phase reveals that an earlier decision needs revisiting, say so explicitly rather than quietly patching around it.
3. **Verify against real APIs early.** Don't build the ML/scoring/visualization layers against mocked data and hope the real AbuseIPDB/Cloudflare Radar responses match your assumptions — pull real data in Phase 1 and confirm the shape before building on top of it.
4. **Budget-conscious execution.** I'm running you at low/default effort on a cost-sensitive plan. Prefer concrete, direct implementation over excessive exploratory back-and-forth. If something is genuinely ambiguous and the choice matters (not a trivial style preference), ask me directly rather than guessing expensively across multiple attempts.
5. **No invented API behavior.** If you're not certain how an AbuseIPDB or Cloudflare Radar endpoint actually responds, say so and either fetch their current docs or ask me to confirm, rather than assuming a response shape from training data — these APIs change.
6. **Security doc is a hard floor, not a suggestion.** Never commit secrets. Never persist raw IPs to a client-reachable table. Rate-limit public endpoints. These aren't optional polish — treat them as acceptance criteria on every phase that touches them.
7. **Commit as you go**, following the phase boundaries in `05_FEATURE_TICKETS.md` — one clean, reviewable commit (or small set of commits) per phase, not one giant commit at the end.
8. **Flag scope creep.** If a phase is ballooning beyond what its ticket describes, stop and tell me before continuing, rather than silently building a bigger feature than scoped.

## Current phase
Phase 0 and Phase 1 are complete and committed. Phase 2 (ML live composite risk scorer) is
**code-complete but the trained artifact is not yet generated** — blocked on an exhausted
API quota, not on anything left to build. To finish Phase 2:

1. Wait until the `/blacklist` daily quota resets (2026-07-12 00:00 UTC — see below).
2. From `backend/`, with `.env` populated: `./venv/Scripts/python.exe -m app.ml.training.train`
3. This generates `app/ml/model.pkl` + `app/ml/model_card.md`. Review the model card's
   held-out metrics and the model-vs-AbuseIPDB-confidence correlation note, then commit both
   files as the final Phase 2 commit ("Phase 2: trained risk scorer artifact").
4. Optionally re-run `scripts/run_ingest_once.py` afterward to confirm live events get a
   populated, non-null `risk_score`.

### Important API constraints discovered during Phase 1/2 (verified live, not assumed)
- AbuseIPDB's bulk `/blacklist` endpoint does not return category codes, total report count,
  or distinct-reporter count. Those only come from the per-IP `/check?verbose` endpoint.
- **`/blacklist` is capped at 5 requests/day** on the free tier (confirmed via a live 429:
  "Daily rate limit of 5 requests exceeded for this endpoint"). This is why the ingestion
  pipeline (`app/scheduler.py`) is split into `run_blacklist_pull_cycle` (infrequent, quota-
  guarded via the `api_quota_usage` table, default every 6h) and `run_drain_cycle` (fast
  ~30s cadence, drains an in-memory backlog so the globe still animates between infrequent
  source refreshes). Do not revert to polling `/blacklist` directly on the fast cadence.
- `/check` has a separate, more generous 1,000/day quota, also guarded via `api_quota_usage`
  (`CHECK_DAILY_SAFE_MAX` in `app/scheduler.py`) since every newly-drained IP consumes one.
- The architecture doc's original proxy-label definition (positive = categories intersect
  {DDoS(4), Port-Scan(14), Brute-Force(18)}) was reverted after a live pull showed it was
  ~100% positive (18 and 14 are bundled onto nearly every AbuseIPDB report) — see
  `app/ml/features.py` for the corrected definition (category 4 alone) and full rationale.

## Naming note
"CyberPulse" is only an internal working title used in these docs/commit messages/repo folder name for organizational convenience. **The deployed product UI must not display any product name, logo, or wordmark** . Do not add a title/header/logo to the app itself just because the docs need a label to refer to the project by.
