"""Sets test-only env vars before any `app.*` module is imported (Settings()
is instantiated at import time), so tests never touch the real dev DB, real
API keys, or spin up the real background scheduler against live APIs.
"""

import os
import pathlib

TEST_DB_PATH = pathlib.Path(__file__).parent / "test_cyberpulse.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["IP_HASH_SALT"] = "test-salt-not-for-production"
os.environ["ABUSEIPDB_API_KEY"] = "test-key"
os.environ["CLOUDFLARE_RADAR_API_TOKEN"] = "test-token"
os.environ["ENVIRONMENT"] = "development"
os.environ["ENABLE_SCHEDULER"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.db.session import engine, init_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _test_db():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    init_db()
    yield
    engine.dispose()  # release SQLite's file handle before removing it (Windows)
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
