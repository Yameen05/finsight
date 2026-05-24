"""Unit tests for the news agent node."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents.nodes import news_agent as news_agent_mod
from app.config import get_settings
from app.schemas.research import NewsFindings
from app.services.news_client import Article, NewsAPIError


def _fake_openai_returning(content: str):
    class _C:
        async def create(self, **_kw):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )

    class _Chat:
        completions = _C()

    return SimpleNamespace(chat=_Chat())


def _safe_clear(fn):
    if hasattr(fn, "cache_clear"):
        fn.cache_clear()


@pytest.fixture(autouse=True)
def reset_caches():
    get_settings.cache_clear()
    _safe_clear(news_agent_mod._client)
    news_agent_mod._reset_news_cache()
    yield
    get_settings.cache_clear()
    _safe_clear(news_agent_mod._client)
    news_agent_mod._reset_news_cache()


async def test_news_agent_skips_when_key_missing(monkeypatch):
    monkeypatch.setenv("NEWS_API_KEY", "")
    result = await news_agent_mod.news_agent({"ticker": "AAPL"})
    findings: NewsFindings = result["news"]
    assert findings.status == "skipped"
    assert findings.error and "NEWS_API_KEY" in findings.error


async def test_news_agent_happy_path(monkeypatch):
    monkeypatch.setenv("NEWS_API_KEY", "key")

    async def fake_lookup_company_name(_ticker, client=None):
        return "Apple Inc."

    async def fake_fetch(_company, days=None, limit=None):
        return [
            Article(
                title="Apple posts record-breaking quarterly earnings, shares surge",
                description="Strong iPhone sales drove the beat.",
                source="Reuters",
                url="u1",
                published_at="2026-05-22T12:00:00Z",
            ),
            Article(
                title="Apple invests in new manufacturing line",
                description="Bullish expansion announced.",
                source="Bloomberg",
                url="u2",
                published_at="2026-05-21T09:00:00Z",
            ),
        ]

    monkeypatch.setattr(news_agent_mod.sec_client, "lookup_company_name", fake_lookup_company_name)
    monkeypatch.setattr(news_agent_mod, "fetch_recent_articles", fake_fetch)
    monkeypatch.setattr(
        news_agent_mod, "_client", lambda: _fake_openai_returning("Sentiment is broadly positive.")
    )

    result = await news_agent_mod.news_agent({"ticker": "AAPL"})
    findings: NewsFindings = result["news"]
    assert findings.status == "ok"
    assert findings.article_count == 2
    assert findings.sentiment_score is not None
    assert findings.sentiment_score > 0
    assert findings.summary == "Sentiment is broadly positive."


async def test_news_agent_no_articles(monkeypatch):
    monkeypatch.setenv("NEWS_API_KEY", "key")

    async def fake_lookup_company_name(_ticker, client=None):
        return "Obscure Corp"

    async def fake_fetch(_company, days=None, limit=None):
        return []

    monkeypatch.setattr(news_agent_mod.sec_client, "lookup_company_name", fake_lookup_company_name)
    monkeypatch.setattr(news_agent_mod, "fetch_recent_articles", fake_fetch)

    result = await news_agent_mod.news_agent({"ticker": "OBSC"})
    findings: NewsFindings = result["news"]
    assert findings.status == "ok"
    assert findings.article_count == 0
    assert findings.sentiment_score == 0.0
    assert "No recent articles" in (findings.summary or "")


async def test_news_agent_unknown_ticker(monkeypatch):
    monkeypatch.setenv("NEWS_API_KEY", "key")

    async def boom(_ticker, client=None):
        raise ValueError("Unknown ticker: ZZZZ")

    monkeypatch.setattr(news_agent_mod.sec_client, "lookup_company_name", boom)

    result = await news_agent_mod.news_agent({"ticker": "ZZZZ"})
    findings: NewsFindings = result["news"]
    assert findings.status == "error"
    assert "Unknown ticker" in (findings.error or "")


async def test_news_agent_handles_api_error(monkeypatch):
    monkeypatch.setenv("NEWS_API_KEY", "key")

    async def fake_lookup_company_name(_ticker, client=None):
        return "Apple Inc."

    async def fake_fetch(_company, days=None, limit=None):
        raise NewsAPIError("HTTP 429: rate limit")

    monkeypatch.setattr(news_agent_mod.sec_client, "lookup_company_name", fake_lookup_company_name)
    monkeypatch.setattr(news_agent_mod, "fetch_recent_articles", fake_fetch)

    result = await news_agent_mod.news_agent({"ticker": "AAPL"})
    findings: NewsFindings = result["news"]
    assert findings.status == "error"
    assert "rate limit" in (findings.error or "")
