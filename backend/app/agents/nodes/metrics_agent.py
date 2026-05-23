"""Financial Metrics agent — Phase 4 stub.

Real implementation in Phase 4 will use yFinance to pull revenue, EPS, P/E,
margins, debt/equity, and the 52-week range.
"""

from __future__ import annotations

from app.agents.state import ResearchState
from app.schemas.research import MetricsFindings


async def metrics_agent(state: ResearchState) -> dict:
    return {
        "metrics": MetricsFindings(
            status="not_implemented",
            error="Metrics agent arrives in Phase 4 (yFinance integration).",
        )
    }
