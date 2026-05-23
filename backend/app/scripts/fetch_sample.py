"""CLI: python -m app.scripts.fetch_sample AAPL"""

from __future__ import annotations

import asyncio
import sys

from app.services.sec_client import fetch_latest_10k


async def main(ticker: str) -> None:
    filing = await fetch_latest_10k(ticker)
    print(f"Ticker:        {filing.ticker}")
    print(f"CIK:           {filing.cik}")
    print(f"Form:          {filing.form}")
    print(f"Accession:     {filing.accession}")
    print(f"Filing date:   {filing.filing_date}")
    print(f"Primary doc:   {filing.primary_document}")
    print(f"Text length:   {len(filing.raw_text):,} chars")
    print("--- head ---")
    print(filing.raw_text[:800])


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    asyncio.run(main(ticker))
