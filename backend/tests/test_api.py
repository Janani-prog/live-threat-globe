import datetime

from app.db.models import Event
from app.db.session import get_session


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_pipeline_reflects_real_state(client):
    """ENABLE_SCHEDULER=false in tests (see conftest.py), so this must
    honestly report the scheduler as inactive — not a hardcoded "active"."""
    r = client.get("/health/pipeline")
    assert r.status_code == 200
    body = r.json()
    assert body["ingestion_engine"]["active"] is False
    assert body["ml_classifier"]["loaded"] is True
    assert body["ml_classifier"]["model_type"] == "LogisticRegression"


def test_events_recent_empty(client):
    r = client.get("/events/recent")
    assert r.status_code == 200
    assert r.json() == []


def test_events_recent_rejects_invalid_pagination(client):
    assert client.get("/events/recent?limit=0").status_code == 422
    assert client.get("/events/recent?limit=99999").status_code == 422
    assert client.get("/events/recent?offset=-1").status_code == 422


def test_events_recent_returns_data_with_null_risk_score(client):
    session = get_session()
    session.add(
        Event(
            ip_hash="abc123",
            lat=1.0,
            lon=2.0,
            country="US",
            asn="AS1 Example",
            category="4",
            confidence_source=90,
            risk_score=None,
            reported_at=datetime.datetime.utcnow(),
        )
    )
    session.commit()
    session.close()

    r = client.get("/events/recent?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["ip_hash"] == "abc123"
    assert body[0]["risk_score"] is None
    assert "ip" not in body[0]  # only the hash is ever exposed, never the raw IP


def test_stats_summary(client):
    r = client.get("/stats/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total_events"] >= 1
    assert isinstance(body["top_countries"], list)


def test_stats_timeseries(client):
    r = client.get("/stats/timeseries")
    assert r.status_code == 200
    assert "points" in r.json()


def test_stats_timeseries_rejects_invalid_minutes(client):
    assert client.get("/stats/timeseries?minutes=0").status_code == 422
    assert client.get("/stats/timeseries?minutes=999999").status_code == 422
