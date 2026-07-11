from app import scheduler
from app.config import BLACKLIST_DAILY_SAFE_MAX
from app.ingestion import abuseipdb


def _reset_backlog():
    scheduler._backlog.clear()


def test_blacklist_pull_falls_back_to_open_feeds_when_quota_exhausted(monkeypatch):
    """The scenario that actually happened in production: /blacklist's
    5-req/day quota (shared across every consumer of the same AbuseIPDB
    key) was already exhausted by local dev testing before the live
    scheduler got a chance to call it.
    """
    _reset_backlog()

    session = scheduler.get_session()
    try:
        for _ in range(BLACKLIST_DAILY_SAFE_MAX):
            assert scheduler._try_consume_quota(session, "blacklist_calls", BLACKLIST_DAILY_SAFE_MAX)
    finally:
        session.close()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("fetch_blacklist should not be called once the quota guard blocks it")

    monkeypatch.setattr(abuseipdb, "fetch_blacklist", fail_if_called)
    monkeypatch.setattr(scheduler.open_feeds, "sample_candidate_ips", lambda n, seed=None: ["9.9.9.9", "8.8.4.4"])

    queued = scheduler.run_blacklist_pull_cycle()

    assert queued == 2
    assert len(scheduler._backlog) == 2
    assert {e.ip for e in scheduler._backlog} == {"9.9.9.9", "8.8.4.4"}
    _reset_backlog()


def test_blacklist_pull_falls_back_when_blacklist_returns_nothing_new(monkeypatch):
    """Even with quota available, an empty/all-already-seen /blacklist
    response should still trigger the open-feeds fallback rather than
    leaving the backlog empty for a whole ~6h cycle."""
    _reset_backlog()

    # Fresh quota row for a date guaranteed not to collide with other tests.
    monkeypatch.setattr(scheduler, "_today", lambda: "2099-01-01")

    monkeypatch.setattr(abuseipdb, "fetch_blacklist", lambda **kwargs: [])
    monkeypatch.setattr(scheduler.open_feeds, "sample_candidate_ips", lambda n, seed=None: ["1.2.3.4"])

    queued = scheduler.run_blacklist_pull_cycle()

    assert queued == 1
    assert scheduler._backlog[0].ip == "1.2.3.4"
    _reset_backlog()
