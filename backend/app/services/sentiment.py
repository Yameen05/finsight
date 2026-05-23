"""Sentiment scoring for news headlines using VADER.

VADER is rule-based and lexicon-driven; it works well on short, news-style text
and ships as pure Python with no model download. The `compound` score is a
normalized aggregate in [-1.0, 1.0] which matches our `NewsFindings.sentiment_score`
field exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.services.news_client import Article


@dataclass(slots=True)
class ScoredArticle:
    article: Article
    score: float  # VADER compound, in [-1, 1]


@lru_cache(maxsize=1)
def _analyzer() -> SentimentIntensityAnalyzer:
    return SentimentIntensityAnalyzer()


def score_text(text: str) -> float:
    if not text.strip():
        return 0.0
    return float(_analyzer().polarity_scores(text)["compound"])


def score_articles(articles: list[Article]) -> tuple[float, list[ScoredArticle]]:
    """Return (aggregate_score, per_article_scores).

    Each article is scored on `title + ". " + description` so longer context
    improves accuracy without diluting headline-driven signal.
    """
    if not articles:
        return 0.0, []
    scored = [
        ScoredArticle(
            article=a,
            score=score_text(f"{a.title}. {a.description}".strip()),
        )
        for a in articles
    ]
    aggregate = sum(s.score for s in scored) / len(scored)
    # Clamp for safety against floating drift.
    aggregate = max(-1.0, min(1.0, aggregate))
    return aggregate, scored
