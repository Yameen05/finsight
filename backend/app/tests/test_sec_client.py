"""Unit tests for sec_client using mocked HTTP responses.

We do not hit the live SEC API in CI; live calls can be done via the
`make fetch-sample` helper for manual verification.
"""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from app.services import sec_client

SAMPLE_TICKER_JSON = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp."},
}

SAMPLE_SUBMISSIONS = {
    "cik": "0000320193",
    "filings": {
        "recent": {
            "form": ["10-K", "10-Q", "8-K"],
            "accessionNumber": [
                "0000320193-24-000123",
                "0000320193-24-000099",
                "0000320193-24-000050",
            ],
            "filingDate": ["2024-11-01", "2024-08-02", "2024-07-30"],
            "primaryDocument": ["aapl-10k.htm", "aapl-10q.htm", "aapl-8k.htm"],
        }
    },
}

SAMPLE_HTML = """
<html><head><title>10-K</title></head>
<body>
  <p>Risk Factors</p>
  <p>Our business faces material risks including supply-chain disruption.</p>
  <script>nope()</script>
</body></html>
"""


@pytest.fixture(autouse=True)
def reset_ticker_cache():
    sec_client._ticker_cache = None
    yield
    sec_client._ticker_cache = None


async def test_lookup_cik_resolves_ticker(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=sec_client.TICKER_LOOKUP_URL, json=SAMPLE_TICKER_JSON)
    cik = await sec_client.lookup_cik("AAPL")
    assert cik == "0000320193"


async def test_lookup_cik_unknown_ticker_raises(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=sec_client.TICKER_LOOKUP_URL, json=SAMPLE_TICKER_JSON)
    with pytest.raises(ValueError, match="Unknown ticker"):
        await sec_client.lookup_cik("NOPE")


async def test_fetch_latest_10k(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=sec_client.TICKER_LOOKUP_URL, json=SAMPLE_TICKER_JSON)
    httpx_mock.add_response(
        url=sec_client.SUBMISSIONS_URL_TEMPLATE.format(cik="0000320193"),
        json=SAMPLE_SUBMISSIONS,
    )
    httpx_mock.add_response(
        url="https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-10k.htm",
        text=SAMPLE_HTML,
    )

    filing = await sec_client.fetch_latest_10k("AAPL")

    assert filing.ticker == "AAPL"
    assert filing.cik == "0000320193"
    assert filing.form == "10-K"
    assert filing.accession == "0000320193-24-000123"
    assert filing.filing_date == "2024-11-01"
    assert filing.primary_document == "aapl-10k.htm"
    assert "supply-chain disruption" in filing.raw_text
    assert "nope()" not in filing.raw_text  # script stripped


async def test_html_to_text_strips_boilerplate():
    text = sec_client._html_to_text("<html><body>Hello   world\n\n\n</body></html>")
    assert text.strip() == "Hello   world"
