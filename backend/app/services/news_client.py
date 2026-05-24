"""NewsAPI.org client.

Free Developer tier:
- 100 requests/day
- 30-day article window on the `everything` endpoint
- Single endpoint we use: GET /v2/everything

Docs: https://newsapi.org/docs/endpoints/everything
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from app.config import get_settings

NEWS_API_URL = "https://newsapi.org/v2/everything"


@dataclass(slots=True)
class Article:
    title: str
    description: str
    source: str
    url: str
    published_at: str  # ISO8601


class NewsAPIError(RuntimeError):
    pass


async def fetch_recent_articles(
    company_name: str,
    days: int | None = None,
    limit: int | None = None,
) -> list[Article]:
    """Return up to `limit` recent articles mentioning `company_name`.

    Raises NewsAPIError if no API key configured or the request fails.
    """
    settings = get_settings()
    api_key = settings.news_api_key
    if not api_key:
        raise NewsAPIError("NEWS_API_KEY not set")

    days = days or settings.news_lookback_days
    limit = limit or settings.news_max_articles

    from_dt = datetime.now(UTC) - timedelta(days=days)
    params = {
        "q": f'"{company_name}"',  # quoted to avoid loose token matches
        "from": from_dt.strftime("%Y-%m-%d"),
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": min(limit, 100),
        "apiKey": api_key,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(NEWS_API_URL, params=params)
        if r.status_code != 200:
            raise NewsAPIError(
                f"NewsAPI HTTP {r.status_code}: {r.text[:200]}"
            )
        body = r.json()
        if body.get("status") != "ok":
            raise NewsAPIError(
                f"NewsAPI error: {body.get('code')} {body.get('message')}"
            )

    return [
        Article(
            title=a.get("title") or "",
            description=a.get("description") or "",
            source=(a.get("source") or {}).get("name") or "",
            url=a.get("url") or "",
            published_at=a.get("publishedAt") or "",
        )
        for a in (body.get("articles") or [])[:limit]
        if a.get("title")
    ]
