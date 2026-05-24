"""Tests for the research-history persistence layer."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.db import (
    init_db,
    list_runs_for_ticker,
    save_run,
    session_scope,
)


async def _open_session() -> AsyncSession:
    async for s in session_scope():
        return s
    raise RuntimeError("no session")


async def test_save_and_list_runs():
    await init_db()
    session = await _open_session()
    try:
        run = await save_run(
            session,
            ticker="AAPL",
            recommendation="Buy",
            justification="Strong fundamentals.",
            sentiment_score=0.3,
            payload={"foo": "bar"},
            duration_ms=1234.5,
            cost_usd=0.0021,
            request_id="rid-1",
        )
        assert run.id is not None
        assert run.ticker == "AAPL"
    finally:
        await session.close()

    session = await _open_session()
    try:
        rows = await list_runs_for_ticker(session, "AAPL")
        assert len(rows) == 1
        assert rows[0].recommendation == "Buy"
        assert rows[0].cost_usd == pytest.approx(0.0021)
    finally:
        await session.close()


async def test_history_endpoint_returns_runs(client):
    # No runs yet → empty list
    res = client.get("/research/history/AAPL")
    assert res.status_code == 200
    assert res.json() == {"ticker": "AAPL", "runs": []}


async def test_history_rejects_bad_ticker(client):
    res = client.get("/research/history/!!!")
    assert res.status_code == 400
