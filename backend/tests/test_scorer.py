import datetime

from app.ml import scorer


def _score_dummy():
    return scorer.score(
        total_reports=5,
        num_distinct_users=3,
        category_ids=[18],
        usage_type="Fixed Line ISP",
        last_reported_at=datetime.datetime.utcnow(),
        country="US",
    )


def test_score_returns_none_when_model_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(scorer, "MODEL_PATH", tmp_path / "does-not-exist.pkl")
    monkeypatch.setattr(scorer, "_artifact", None)
    assert _score_dummy() is None


def test_score_returns_none_when_model_corrupted(monkeypatch, tmp_path):
    bad_model = tmp_path / "corrupted.pkl"
    bad_model.write_bytes(b"not a valid joblib pickle")
    monkeypatch.setattr(scorer, "MODEL_PATH", bad_model)
    monkeypatch.setattr(scorer, "_artifact", None)
    assert _score_dummy() is None
