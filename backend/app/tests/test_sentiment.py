from app.services.news_client import Article
from app.services.sentiment import score_articles, score_text


def _article(title: str, description: str = "") -> Article:
    return Article(title=title, description=description, source="", url="", published_at="")


def test_score_text_polarity():
    pos = score_text("Apple posts record-breaking quarterly earnings, shares surge")
    neg = score_text("Tech giant under investigation for fraud, layoffs ahead")
    neu = score_text("Apple Inc. is headquartered in Cupertino")
    assert pos > 0.1
    assert neg < -0.1
    assert -0.1 <= neu <= 0.1


def test_score_articles_empty():
    agg, scored = score_articles([])
    assert agg == 0.0
    assert scored == []


def test_score_articles_aggregate():
    arts = [
        _article("Stock soars on strong earnings"),
        _article("Company faces lawsuit and layoffs"),
        _article("Stock surges to new high"),
    ]
    agg, scored = score_articles(arts)
    assert -1.0 <= agg <= 1.0
    assert len(scored) == 3
    # Two positive, one negative — aggregate should lean positive.
    assert agg > 0
