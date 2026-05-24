"""End-to-end smoke test for the assembled LangGraph.

All external dependencies (vectorstore, OpenAI, NewsAPI, yfinance) are stubbed;
this verifies fan-out → fan-in → synthesizer wiring and that all four state
slots end up populated by the time the graph exits.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.agents import graph as graph_mod
from app.agents.nodes import metrics_agent as metrics_agent_mod
from app.agents.nodes import news_agent as news_agent_mod
from app.agents.nodes import sec_agent as sec_agent_mod
from app.agents.nodes import synthesizer as synth_mod
from app.config import get_settings
from app.services.metrics_client import Metrics


def _fake_openai_returning(content: str):
    class _C:
        async def create(self, **_kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    class _Chat:
        completions = _C()

    return SimpleNamespace(chat=_Chat())


@pytest.fixture
def stub_externals(monkeypatch):
    sec_agent_mod._client.cache_clear()
    news_agent_mod._client.cache_clear()
    synth_mod._client.cache_clear()
    graph_mod.get_graph.cache_clear()
    get_settings.cache_clear()

    # --- SEC ---
    async def fake_embed_query(_t):
        return [0.0] * 1536

    async def fake_query(_ticker, _vec, top_k=5):
        from app.services.vectorstore import QueryMatch

        return [
            QueryMatch(
                score=0.8,
                text="Apple faces supply-chain risk.",
                metadata={"accession": "ACC-1", "chunk_index": 0, "ticker": "AAPL"},
            )
        ]

    monkeypatch.setattr(sec_agent_mod, "embed_query", fake_embed_query)
    monkeypatch.setattr(sec_agent_mod.vectorstore, "query", fake_query)
    monkeypatch.setattr(
        sec_agent_mod, "_client", lambda: _fake_openai_returning("Short answer.")
    )

    # --- News ---
    monkeypatch.setenv("NEWS_API_KEY", "test-key")

    async def fake_lookup_company_name(_ticker, client=None):
        return "Apple Inc."

    async def fake_fetch_articles(_company, days=None, limit=None):
        from app.services.news_client import Article

        return [
            Article(
                title="Apple reports strong quarterly earnings",
                description="Revenue beats estimates.",
                source="Reuters",
                url="u",
                published_at="2026-05-22T12:00:00Z",
            )
        ]

    monkeypatch.setattr(news_agent_mod.sec_client, "lookup_company_name", fake_lookup_company_name)
    monkeypatch.setattr(news_agent_mod, "fetch_recent_articles", fake_fetch_articles)
    monkeypatch.setattr(
        news_agent_mod, "_client", lambda: _fake_openai_returning("News sentiment is positive.")
    )

    # --- Metrics ---
    def fake_fetch_metrics(_ticker):
        return Metrics(
            revenue=394e9,
            eps=6.16,
            pe_ratio=30.5,
            profit_margin=0.253,
            debt_to_equity=145.0,
            week_52_low=164.08,
            week_52_high=237.49,
        )

    monkeypatch.setattr(metrics_agent_mod, "fetch_metrics", fake_fetch_metrics)

    # --- Synthesizer ---
    synth_payload = json.dumps(
        {
            "recommendation": "Buy",
            "justification": "Strong fundamentals (25% margin), positive sentiment, manageable supply-chain risk.",
            "company_overview": "Apple makes consumer electronics.",
            "financial_health": "TTM revenue $394B with 25.3% profit margin.",
            "key_risks": ["Supply chain"],
            "news_summary": "Recent earnings beat estimates.",
        }
    )
    monkeypatch.setattr(synth_mod, "_client", lambda: _fake_openai_returning(synth_payload))

    yield
    get_settings.cache_clear()


async def test_graph_end_to_end_all_agents_ok(stub_externals):
    result = await graph_mod.run_research("AAPL")

    assert result.ticker == "AAPL"
    assert result.sec.status == "ok"
    assert result.news.status == "ok"
    assert result.metrics.status == "ok"
    assert result.metrics.profit_margin == pytest.approx(0.253)

    # Synthesizer received all three signals → real recommendation.
    assert result.report.recommendation == "Buy"
    assert "Supply chain" in result.report.key_risks
    assert result.report.news_summary is not None
