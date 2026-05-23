"""Shared LangGraph state for the research pipeline."""

from __future__ import annotations

from typing import TypedDict

from app.schemas.research import (
    MetricsFindings,
    NewsFindings,
    ResearchReport,
    SECFindings,
)


class ResearchState(TypedDict, total=False):
    ticker: str
    # Each agent node populates its slot; missing slots are treated as "skipped".
    sec: SECFindings
    news: NewsFindings
    metrics: MetricsFindings
    report: ResearchReport
