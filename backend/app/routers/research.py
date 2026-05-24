"""Research orchestration endpoints.

  POST /research/{ticker}              run the graph, persist, return report + cost
  GET  /research/{ticker}/stream       same, but emit per-node Server-Sent Events
  GET  /research/history/{ticker}      list recent stored runs
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.agents.graph import get_graph, run_research
from app.config import get_settings
from app.limiter import limiter
from app.observability.cost import CostTracker, start_tracking
from app.observability.logging import get_logger, get_request_id
from app.persistence.db import list_runs_for_ticker, save_run, session_scope
from app.schemas.research import (
    MetricsFindings,
    NewsFindings,
    ResearchReport,
    ResearchResponse,
    SECFindings,
)

router = APIRouter()
log = get_logger(__name__)


# ----- helpers -----

def _validate_ticker(raw: str) -> str:
    t = (raw or "").strip().upper()
    if not t or len(t) > 10 or not t.replace(".", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid ticker")
    return t


def _state_to_response(ticker: str, state: dict) -> ResearchResponse:
    return ResearchResponse(
        ticker=ticker,
        sec=state.get("sec") or SECFindings(status="skipped"),
        news=state.get("news") or NewsFindings(status="skipped"),
        metrics=state.get("metrics") or MetricsFindings(status="skipped"),
        report=state.get("report")
        or ResearchReport(
            ticker=ticker,
            recommendation="Pending",
            justification="Graph did not produce a report.",
            company_overview="",
            financial_health="",
        ),
    )


class ResearchEnvelope(BaseModel):
    """Wraps ResearchResponse with operational metadata."""

    request_id: str = Field(default="")
    duration_ms: float = 0.0
    cost: dict[str, Any] = Field(default_factory=dict)
    persisted_id: int | None = None
    result: ResearchResponse


class HistoryEntry(BaseModel):
    id: int
    ticker: str
    recommendation: str
    justification: str
    sentiment_score: float | None = None
    duration_ms: float | None = None
    cost_usd: float | None = None
    created_at: datetime


class HistoryResponse(BaseModel):
    ticker: str
    runs: list[HistoryEntry]


# ----- POST /research/{ticker} -----

@router.post("/{ticker}", response_model=ResearchEnvelope)
@limiter.limit(lambda: get_settings().rate_limit_research)
async def research(
    request: Request,
    response: Response,
    ticker: str,
    session: AsyncSession = Depends(session_scope),
) -> ResearchEnvelope:
    ticker = _validate_ticker(ticker)
    tracker = start_tracking()
    rid = get_request_id()
    log.info("research_started", extra={"ticker": ticker})

    started = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            run_research(ticker),
            timeout=get_settings().request_timeout_seconds,
        )
    except TimeoutError as e:
        log.warning("research_timeout", extra={"ticker": ticker})
        raise HTTPException(status_code=504, detail="Research timed out") from e
    duration_ms = round((time.perf_counter() - started) * 1000, 2)

    cost_payload = tracker.to_dict()
    response.headers["x-cost-usd"] = f"{tracker.total_usd:.6f}"
    response.headers["x-duration-ms"] = f"{duration_ms:.2f}"

    run = await save_run(
        session,
        ticker=ticker,
        recommendation=result.report.recommendation,
        justification=result.report.justification,
        sentiment_score=result.news.sentiment_score,
        payload=result.model_dump(),
        duration_ms=duration_ms,
        cost_usd=tracker.total_usd,
        request_id=rid,
    )
    log.info(
        "research_completed",
        extra={
            "ticker": ticker,
            "recommendation": result.report.recommendation,
            "duration_ms": duration_ms,
            "cost_usd": tracker.total_usd,
            "run_id": run.id,
        },
    )

    return ResearchEnvelope(
        request_id=rid,
        duration_ms=duration_ms,
        cost=cost_payload,
        persisted_id=run.id,
        result=result,
    )


# ----- GET /research/{ticker}/stream -----

async def _sse_stream(ticker: str, tracker: CostTracker, rid: str):
    """Run the graph via astream() and yield SSE events for each node update."""
    graph = get_graph()
    started = time.perf_counter()

    yield {
        "event": "started",
        "data": json.dumps({"ticker": ticker, "request_id": rid}),
    }

    final_state: dict = {}
    try:
        async for chunk in graph.astream({"ticker": ticker}):
            # `chunk` is {node_name: partial_state}
            for node_name, partial in chunk.items():
                final_state.update(partial)
                yield {
                    "event": "node_completed",
                    "data": json.dumps(
                        {"node": node_name, "payload": _serializable(partial)},
                        default=str,
                    ),
                }
    except Exception as e:  # noqa: BLE001
        log.exception("research_stream_failed", extra={"ticker": ticker})
        yield {
            "event": "error",
            "data": json.dumps({"detail": str(e), "error_type": type(e).__name__}),
        }
        return

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    result = _state_to_response(ticker, final_state)

    # Persist (best-effort; SSE consumer doesn't need to wait).
    persisted_id = None
    try:
        async for session in session_scope():
            run = await save_run(
                session,
                ticker=ticker,
                recommendation=result.report.recommendation,
                justification=result.report.justification,
                sentiment_score=result.news.sentiment_score,
                payload=result.model_dump(),
                duration_ms=duration_ms,
                cost_usd=tracker.total_usd,
                request_id=rid,
            )
            persisted_id = run.id
            break
    except Exception:  # noqa: BLE001
        log.exception("research_stream_persist_failed", extra={"ticker": ticker})

    yield {
        "event": "completed",
        "data": json.dumps(
            {
                "request_id": rid,
                "duration_ms": duration_ms,
                "cost": tracker.to_dict(),
                "persisted_id": persisted_id,
                "result": result.model_dump(),
            },
            default=str,
        ),
    }


def _serializable(d: dict) -> dict:
    out: dict = {}
    for k, v in d.items():
        out[k] = v.model_dump() if hasattr(v, "model_dump") else v
    return out


@router.get("/{ticker}/stream")
@limiter.limit(lambda: get_settings().rate_limit_research)
async def research_stream(request: Request, ticker: str) -> EventSourceResponse:
    ticker = _validate_ticker(ticker)
    tracker = start_tracking()
    rid = get_request_id()
    log.info("research_stream_started", extra={"ticker": ticker})
    return EventSourceResponse(_sse_stream(ticker, tracker, rid))


# ----- GET /research/history/{ticker} -----

@router.get("/history/{ticker}", response_model=HistoryResponse)
async def history(
    ticker: str,
    limit: int = 20,
    session: AsyncSession = Depends(session_scope),
) -> HistoryResponse:
    ticker = _validate_ticker(ticker)
    rows = await list_runs_for_ticker(session, ticker, limit=min(max(limit, 1), 100))
    return HistoryResponse(
        ticker=ticker,
        runs=[
            HistoryEntry(
                id=r.id,
                ticker=r.ticker,
                recommendation=r.recommendation,
                justification=r.justification,
                sentiment_score=r.sentiment_score,
                duration_ms=r.duration_ms,
                cost_usd=r.cost_usd,
                created_at=r.created_at,
            )
            for r in rows
        ],
    )
