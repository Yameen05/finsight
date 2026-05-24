"""Unit tests for the synthesizer node."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.agents.nodes import synthesizer as synth_mod
from app.config import get_settings
from app.schemas.research import (
    MetricsFindings,
    NewsFindings,
    ResearchReport,
    SECFinding,
    SECFindings,
)


def _fake_openai_returning(content: str):
    class _C:
        async def create(self, **_kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    class _Chat:
        completions = _C()

    return SimpleNamespace(chat=_Chat())


def _safe_clear(fn):
    """Call .cache_clear() if available — monkey-patched lambdas may have replaced it."""
    if hasattr(fn, "cache_clear"):
        fn.cache_clear()


@pytest.fixture(autouse=True)
def reset_caches():
    _safe_clear(synth_mod._client)
    get_settings.cache_clear()
    yield
    _safe_clear(synth_mod._client)
    get_settings.cache_clear()


def _ok_state() -> dict:
    return {
        "ticker": "AAPL",
        "sec": SECFindings(
            status="ok",
            findings=[SECFinding(question="risks?", answer="Supply chain.", source_chunks=3)],
            accession="ACC-1",
        ),
        "news": NewsFindings(status="ok", sentiment_score=0.4, summary="Positive", article_count=10),
        "metrics": MetricsFindings(
            status="ok",
            revenue=3.9e11,
            eps=6.16,
            pe_ratio=30.5,
            profit_margin=0.25,
            debt_to_equity=145.0,
            week_52_low=164.0,
            week_52_high=237.0,
        ),
    }


async def test_synthesizer_returns_buy_when_signals_align(monkeypatch):
    monkeypatch.setattr(
        synth_mod,
        "_client",
        lambda: _fake_openai_returning(
            json.dumps(
                {
                    "recommendation": "Buy",
                    "justification": "Strong margins + positive sentiment.",
                    "company_overview": "Apple makes consumer electronics.",
                    "financial_health": "25% profit margin on $390B revenue.",
                    "key_risks": ["Supply chain"],
                    "news_summary": "Positive sentiment last 30 days.",
                }
            )
        ),
    )
    out = await synth_mod.synthesizer(_ok_state())
    report: ResearchReport = out["report"]
    assert report.recommendation == "Buy"
    assert report.key_risks == ["Supply chain"]


async def test_synthesizer_handles_invalid_json(monkeypatch):
    monkeypatch.setattr(
        synth_mod, "_client", lambda: _fake_openai_returning("not json at all")
    )
    out = await synth_mod.synthesizer(_ok_state())
    report: ResearchReport = out["report"]
    assert report.recommendation == "Pending"
    assert "parse model output" in report.justification


async def test_synthesizer_short_circuits_when_no_agents_usable():
    state = {
        "ticker": "AAPL",
        "sec": SECFindings(status="skipped", error="ingest first"),
        "news": NewsFindings(status="skipped", error="no key"),
        "metrics": MetricsFindings(status="error", error="unknown ticker"),
    }
    out = await synth_mod.synthesizer(state)
    report: ResearchReport = out["report"]
    assert report.recommendation == "Pending"
    assert "No agent" in report.justification


async def test_synthesizer_runs_with_partial_signals(monkeypatch):
    """If only one agent is ok, synth should still try (not short-circuit)."""
    monkeypatch.setattr(
        synth_mod,
        "_client",
        lambda: _fake_openai_returning(
            json.dumps(
                {
                    "recommendation": "Hold",
                    "justification": "Limited data.",
                    "company_overview": "Apple.",
                    "financial_health": "No metrics available.",
                    "key_risks": [],
                    "news_summary": None,
                }
            )
        ),
    )
    state = {
        "ticker": "AAPL",
        "sec": SECFindings(
            status="ok",
            findings=[SECFinding(question="risks?", answer="Supply chain.", source_chunks=2)],
            accession="ACC-1",
        ),
        "news": NewsFindings(status="skipped", error="no key"),
        "metrics": MetricsFindings(status="error", error="unknown ticker"),
    }
    out = await synth_mod.synthesizer(state)
    report: ResearchReport = out["report"]
    assert report.recommendation == "Hold"
