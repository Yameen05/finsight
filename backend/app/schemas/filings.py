from typing import Literal

from pydantic import BaseModel, Field

FilingForm = Literal["10-K", "10-Q"]


class IngestRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker, e.g. AAPL")
    form: FilingForm = "10-K"


class IngestResponse(BaseModel):
    ticker: str
    form: FilingForm
    accession: str
    filing_date: str
    chunks_indexed: int


class QueryRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    question: str = Field(..., min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class QueryMatch(BaseModel):
    score: float
    text: str
    accession: str
    form: FilingForm
    filing_date: str
    chunk_index: int


class QueryResponse(BaseModel):
    ticker: str
    question: str
    matches: list[QueryMatch]
