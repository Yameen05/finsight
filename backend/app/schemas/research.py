from typing import Literal

from pydantic import BaseModel, Field

AgentStatus = Literal["ok", "skipped", "not_implemented", "error"]


class SECFinding(BaseModel):
    question: str
    answer: str
    source_chunks: int = Field(description="How many retrieved chunks were used")


class SECFindings(BaseModel):
    status: AgentStatus
    findings: list[SECFinding] = Field(default_factory=list)
    accession: str | None = None
    error: str | None = None


class NewsFindings(BaseModel):
    status: AgentStatus
    sentiment_score: float | None = Field(default=None, ge=-1.0, le=1.0)
    summary: str | None = None
    article_count: int = 0
    error: str | None = None


class MetricsFindings(BaseModel):
    status: AgentStatus
    revenue: float | None = None
    eps: float | None = None
    pe_ratio: float | None = None
    profit_margin: float | None = None
    debt_to_equity: float | None = None
    week_52_low: float | None = None
    week_52_high: float | None = None
    error: str | None = None


class ResearchReport(BaseModel):
    ticker: str
    recommendation: Literal["Buy", "Hold", "Sell", "Pending"] = "Pending"
    justification: str
    company_overview: str
    financial_health: str
    key_risks: list[str] = Field(default_factory=list)
    news_summary: str | None = None


class ResearchResponse(BaseModel):
    ticker: str
    sec: SECFindings
    news: NewsFindings
    metrics: MetricsFindings
    report: ResearchReport
