from fastapi import APIRouter, HTTPException

from app.schemas.filings import (
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
)
from app.schemas.filings import (
    QueryMatch as QueryMatchSchema,
)
from app.services import sec_client, vectorstore
from app.services.chunker import chunk_filing
from app.services.embeddings import embed_query, embed_texts

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_filing(req: IngestRequest) -> IngestResponse:
    try:
        if req.form == "10-K":
            filing = await sec_client.fetch_latest_10k(req.ticker)
        else:
            filing = await sec_client.fetch_latest_10q(req.ticker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"SEC fetch failed: {e}") from e

    chunks = chunk_filing(filing)
    if not chunks:
        raise HTTPException(status_code=422, detail="Filing produced zero chunks")

    vectors = await embed_texts([c.text for c in chunks])
    indexed = await vectorstore.upsert_chunks(filing.ticker, chunks, vectors)

    return IngestResponse(
        ticker=filing.ticker,
        form=filing.form,
        accession=filing.accession,
        filing_date=filing.filing_date,
        chunks_indexed=indexed,
    )


@router.post("/query", response_model=QueryResponse)
async def query_filing(req: QueryRequest) -> QueryResponse:
    vector = await embed_query(req.question)
    matches = await vectorstore.query(req.ticker, vector, top_k=req.top_k)

    return QueryResponse(
        ticker=req.ticker.upper(),
        question=req.question,
        matches=[
            QueryMatchSchema(
                score=m.score,
                text=m.text,
                accession=m.metadata.get("accession", ""),
                form=m.metadata.get("form", "10-K"),
                filing_date=m.metadata.get("filing_date", ""),
                chunk_index=int(m.metadata.get("chunk_index", 0)),
            )
            for m in matches
        ],
    )
