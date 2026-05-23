"""Synthesizer node.

Takes whatever findings are populated in state and produces a structured
`ResearchReport`. In Phase 2 the LLM is only asked to assemble a coherent
narrative from the SEC findings (since News/Metrics are stubs). Phase 5 will
add the real Buy/Hold/Sell decision logic with all three signals.
"""

from __future__ import annotations

import json
from functools import lru_cache

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agents.state import ResearchState
from app.config import get_settings
from app.schemas.research import ResearchReport

_SYSTEM = (
    "You are a financial research analyst. You will receive a JSON object with "
    "findings from three specialist agents (SEC filings, news, metrics). Some "
    "agents may have returned status='not_implemented' or 'skipped' — in that "
    "case ignore that section gracefully.\n\n"
    "Return ONLY a JSON object matching this schema (no markdown fences):\n"
    "{\n"
    '  "recommendation": "Buy" | "Hold" | "Sell" | "Pending",\n'
    '  "justification": "1-3 sentences",\n'
    '  "company_overview": "1-2 sentences grounded in SEC findings",\n'
    '  "financial_health": "1-2 sentences",\n'
    '  "key_risks": ["risk 1", "risk 2", ...],\n'
    '  "news_summary": "1-2 sentences or null"\n'
    "}\n\n"
    "If news and metrics are not yet available, use recommendation='Pending' "
    "and state in the justification that additional signals are needed."
)


@lru_cache(maxsize=1)
def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


def _state_payload(state: ResearchState) -> dict:
    out = {"ticker": state.get("ticker")}
    for key in ("sec", "news", "metrics"):
        val = state.get(key)
        if val is not None:
            out[key] = val.model_dump() if hasattr(val, "model_dump") else val
    return out


async def synthesizer(state: ResearchState) -> dict:
    ticker = state["ticker"]
    payload = _state_payload(state)

    resp = await _client().chat.completions.create(
        model=get_settings().llm_model,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": json.dumps(payload, default=str)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"

    try:
        data = json.loads(raw)
        report = ResearchReport(
            ticker=ticker,
            recommendation=data.get("recommendation", "Pending"),
            justification=data.get("justification", ""),
            company_overview=data.get("company_overview", ""),
            financial_health=data.get("financial_health", ""),
            key_risks=data.get("key_risks", []) or [],
            news_summary=data.get("news_summary"),
        )
    except (json.JSONDecodeError, ValidationError) as e:
        report = ResearchReport(
            ticker=ticker,
            recommendation="Pending",
            justification=f"Synthesizer failed to parse model output: {e}",
            company_overview="",
            financial_health="",
        )

    return {"report": report}
