from app.services.chunker import _clean, chunk_filing
from app.services.sec_client import Filing


def _make_filing(text: str) -> Filing:
    return Filing(
        ticker="AAPL",
        cik="0000320193",
        form="10-K",
        accession="0000320193-24-000123",
        filing_date="2024-11-01",
        primary_document="aapl-10k.htm",
        raw_text=text,
    )


def test_clean_strips_boilerplate():
    raw = "Item 1.....................Page 5\n\n\n\nBody"
    cleaned = _clean(raw)
    assert "....." not in cleaned
    assert "Body" in cleaned


def test_chunk_filing_produces_chunks_with_metadata():
    text = "Risk factors. " * 500  # ~7000 chars
    filing = _make_filing(text)
    chunks = chunk_filing(filing, chunk_size=500, chunk_overlap=50)

    assert len(chunks) > 1
    for i, c in enumerate(chunks):
        assert c.text
        assert c.metadata["ticker"] == "AAPL"
        assert c.metadata["form"] == "10-K"
        assert c.metadata["accession"] == "0000320193-24-000123"
        assert c.metadata["filing_date"] == "2024-11-01"
        assert c.metadata["chunk_index"] == i


def test_chunk_filing_short_text_single_chunk():
    filing = _make_filing("short body")
    chunks = chunk_filing(filing)
    assert len(chunks) == 1
    assert chunks[0].text == "short body"
    assert chunks[0].metadata["chunk_index"] == 0
