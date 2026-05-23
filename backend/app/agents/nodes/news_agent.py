"""News & Sentiment agent — Phase 3.

Resolves the ticker to a company name via the cached SEC ticker index, fetches
recent headlines from NewsAPI, scores aggregate sentiment with VADER, and asks
gpt-4o-mini for a short narrative summary.

Skips cleanly when NEWS_API_KEY is unset so the rest of the research pipeline
still runs.
"""

from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI

from app.agents.state import ResearchState
from app.config import get_settings
from app.schemas.research import NewsFindings
from app.services import sec_client
from app.services.news_client import Article, NewsAPIError, fetch_recent_articles
from app.services.sentiment import score_articles

_SUMMARY_SYSTEM = (
    "You are a financial-research assistant summarizing recent news for an "
    "investor. Given a company name, an aggregate sentiment score in [-1, 1], "
    "and a list of recent headlines, produce a single 2-3 sentence summary "
    "that captures the dominant themes and whether sentiment skews positive, "
    "negative, or mixed. No bullet points, no preamble."
)


@lru_cache(maxsize=1)
def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


async def _summarize(
    company_name: str, aggregate: float, articles: list[Article]
) -> str:
    if not articles:
        return "No recent news articles were found."
    headlines = "\n".join(
        f"- ({a.published_at[:10]}) {a.title}" for a in articles[:15]
    )
    resp = await _client().chat.completions.create(
        model=get_settings().llm_model,
        messages=[
            {"role": "system", "content": _SUMMARY_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Company: {company_name}\n"
                    f"Aggregate sentiment: {aggregate:.3f}\n\n"
                    f"Recent headlines:\n{headlines}"
                ),
            },
        ],
        temperature=0.2,
        max_tokens=180,
    )
    return (resp.choices[0].message.content or "").strip()


async def news_agent(state: ResearchState) -> dict:
    ticker = state["ticker"]

    if not get_settings().news_api_key:
        return {
            "news": NewsFindings(
                status="skipped",
                error="NEWS_API_KEY not set; news agent skipped.",
            )
        }

    try:
        company_name = await sec_client.lookup_company_name(ticker)
    except ValueError as e:
        return {"news": NewsFindings(status="error", error=str(e))}

    try:
        articles = await fetch_recent_articles(company_name)
    except NewsAPIError as e:
        return {"news": NewsFindings(status="error", error=str(e))}

    if not articles:
        return {
            "news": NewsFindings(
                status="ok",
                sentiment_score=0.0,
                summary=f"No recent articles found for {company_name}.",
                article_count=0,
            )
        }

    aggregate, _scored = score_articles(articles)
    try:
        summary = await _summarize(company_name, aggregate, articles)
    except Exception as e:  # noqa: BLE001 - summary is best-effort
        summary = f"({len(articles)} headlines; summary generation failed: {e})"

    return {
        "news": NewsFindings(
            status="ok",
            sentiment_score=round(aggregate, 4),
            summary=summary,
            article_count=len(articles),
        )
    }
