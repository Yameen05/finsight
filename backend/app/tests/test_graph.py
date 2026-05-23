"""Smoke test for the assembled LangGraph.

All external dependencies (vectorstore, OpenAI) are stubbed; this verifies the
graph wiring (fan-out + fan-in + synthesizer) functions and that all four state
slots end up populated.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.agents import graph as graph_mod
from app.agents.nodes import sec_agent as sec_agent_mod
from app.agents.nodes import synthesizer as synth_mod


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
    synth_mod._client.cache_clear()
    graph_mod.get_graph.cache_clear()

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

    synth_payload = json.dumps(
        {
            "recommendation": "Pending",
            "justification": "News and metrics agents not yet implemented.",
            "company_overview": "Apple makes consumer electronics.",
            "financial_health": "Solid cashflow per filings.",
            "key_risks": ["Supply chain"],
            "news_summary": None,
        }
    )
    monkeypatch.setattr(
        synth_mod, "_client", lambda: _fake_openai_returning(synth_payload)
    )
    yield


async def test_graph_end_to_end(stub_externals):
    result = await graph_mod.run_research("AAPL")

    assert result.ticker == "AAPL"
    assert result.sec.status == "ok"
    assert result.news.status == "not_implemented"
    assert result.metrics.status == "not_implemented"
    assert result.report.recommendation == "Pending"
    assert "News and metrics" in result.report.justification
    assert "Supply chain" in result.report.key_risks
