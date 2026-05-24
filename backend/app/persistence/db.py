"""Async SQLAlchemy engine + session for research history.

SQLite by default (single-file, no external service). Switch to Postgres by
overriding DATABASE_URL with a `postgresql+asyncpg://...` URI.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class ResearchRun(Base):
    """One row per completed /research call."""

    __tablename__ = "research_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    recommendation: Mapped[str] = mapped_column(String(16))
    justification: Mapped[str] = mapped_column(Text)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)  # full ResearchResponse as JSON
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )


_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _ensure_sqlite_dir(url: str) -> None:
    """SQLite URIs point at a file path; create parent dirs so engine creation works."""
    prefix = "sqlite+aiosqlite:///"
    if not url.startswith(prefix):
        return
    raw = url[len(prefix) :]
    if raw == ":memory:" or raw.startswith(":"):
        return
    path = Path(raw).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)


def get_engine():
    global _engine, _sessionmaker
    if _engine is None:
        url = get_settings().database_url
        _ensure_sqlite_dir(url)
        # SQLite doesn't benefit from pool_size; let SA default it.
        _engine = create_async_engine(url, echo=False, future=True)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def session_scope() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: async session yielded as a context manager."""
    get_engine()
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        yield session


async def save_run(
    session: AsyncSession,
    *,
    ticker: str,
    recommendation: str,
    justification: str,
    sentiment_score: float | None,
    payload: dict,
    duration_ms: float | None = None,
    cost_usd: float | None = None,
    request_id: str | None = None,
) -> ResearchRun:
    row = ResearchRun(
        ticker=ticker.upper(),
        recommendation=recommendation,
        justification=justification,
        sentiment_score=sentiment_score,
        payload=payload,
        duration_ms=duration_ms,
        cost_usd=cost_usd,
        request_id=request_id,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_runs_for_ticker(
    session: AsyncSession, ticker: str, limit: int = 20
) -> list[ResearchRun]:
    stmt = (
        select(ResearchRun)
        .where(ResearchRun.ticker == ticker.upper())
        .order_by(ResearchRun.created_at.desc())
        .limit(limit)
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


# Test helper — wiped between tests via dependency override or env var.
def _reset_for_tests() -> None:
    global _engine, _sessionmaker
    _engine = None
    _sessionmaker = None
    if os.environ.get("DATABASE_URL", "").endswith(":memory:"):
        return
