from fastapi import APIRouter, HTTPException

from app.agents.graph import run_research
from app.schemas.research import ResearchResponse

router = APIRouter()


@router.post("/{ticker}", response_model=ResearchResponse)
async def research(ticker: str) -> ResearchResponse:
    ticker = ticker.strip().upper()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker")
    try:
        return await run_research(ticker)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Research failed: {e}") from e
