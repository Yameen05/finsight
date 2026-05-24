"""Shared test fixtures.

Every test runs against an isolated in-memory SQLite DB; the FinSight API key
defaults to unset (auth disabled) unless a test opts in via monkeypatch.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch, tmp_path):
    """Reset settings + point DB at a temp file per-test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("FINSIGHT_API_KEY", "")
    monkeypatch.setenv("RATE_LIMIT_RESEARCH", "1000/minute")
    monkeypatch.setenv("RATE_LIMIT_FILINGS", "1000/minute")
    get_settings.cache_clear()
    # Reset persistence singletons so the new URL is picked up.
    from app.persistence import db as db_mod

    db_mod._engine = None
    db_mod._sessionmaker = None
    yield
    get_settings.cache_clear()
    db_mod._engine = None
    db_mod._sessionmaker = None


@pytest.fixture
def client():
    """A TestClient that runs the app's lifespan (so the DB is created)."""
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c
