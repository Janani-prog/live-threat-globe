"""Pull once from /blacklist (quota-guarded, 5/day free tier) and drain the
resulting backlog, printing what got stored (including risk_score if a
trained model artifact exists).

Usage: python scripts/run_ingest_once.py   (run from backend/, with .env populated)
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO)

from sqlalchemy import select

from app.db.models import Event
from app.db.session import get_session, init_db
from app.ingestion import cloudflare_radar
from app.scheduler import _backlog, run_blacklist_pull_cycle, run_drain_cycle


def main():
    init_db()
    queued = run_blacklist_pull_cycle()
    print(f"\nQueued {queued} new IP(s) from /blacklist (0 likely means the daily quota guard is active).")

    drained = 0
    while _backlog:
        drained += run_drain_cycle()
    print(f"Drained {drained} event(s) into SQLite.\n")

    session = get_session()
    rows = session.execute(select(Event).order_by(Event.id.desc()).limit(10)).scalars().all()
    for row in rows:
        print(
            f"  id={row.id} ip_hash={row.ip_hash[:12]}... lat={row.lat} lon={row.lon} "
            f"country={row.country} asn={row.asn} category={row.category} "
            f"confidence={row.confidence_source} risk_score={row.risk_score} "
            f"reported_at={row.reported_at}"
        )
    session.close()

    print("\nCloudflare Radar snapshot:")
    snapshot = cloudflare_radar.fetch_attack_trends()
    if snapshot:
        print(f"  top_origin_countries[:3] = {snapshot['top_origin_countries'][:3]}")
    else:
        print("  (fetch failed or token missing — see log above)")


if __name__ == "__main__":
    main()
