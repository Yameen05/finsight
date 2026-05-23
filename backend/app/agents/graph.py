"""LangGraph assembly.

Topology:

       ┌──────────┐
       │  start   │
       └────┬─────┘
            │ fan-out (parallel)
   ┌────────┼────────┐
   ▼        ▼        ▼
 sec      news    metrics
   └────────┼────────┘
            │ fan-in
       ┌────▼─────┐
       │synthesize│
       └────┬─────┘
            ▼
           END
"""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.metrics_agent import metrics_agent
from app.agents.nodes.news_agent import news_agent
from app.agents.nodes.sec_agent import sec_agent
from app.agents.nodes.synthesizer import synthesizer
from app.agents.state import ResearchState
from app.schemas.research import (
    MetricsFindings,
    NewsFindings,
    ResearchReport,
    ResearchResponse,
    SECFindings,
)


def _build_graph():
    # Node names cannot collide with state keys, so the nodes get an _agent
    # suffix (and the synthesizer is just "synthesize").
    g = StateGraph(ResearchState)

    g.add_node("sec_agent", sec_agent)
    g.add_node("news_agent", news_agent)
    g.add_node("metrics_agent", metrics_agent)
    g.add_node("synthesize", synthesizer)

    g.add_edge(START, "sec_agent")
    g.add_edge(START, "news_agent")
    g.add_edge(START, "metrics_agent")

    g.add_edge("sec_agent", "synthesize")
    g.add_edge("news_agent", "synthesize")
    g.add_edge("metrics_agent", "synthesize")

    g.add_edge("synthesize", END)

    return g.compile()


@lru_cache(maxsize=1)
def get_graph():
    return _build_graph()


async def run_research(ticker: str) -> ResearchResponse:
    graph = get_graph()
    final_state = await graph.ainvoke({"ticker": ticker.upper()})

    return ResearchResponse(
        ticker=ticker.upper(),
        sec=final_state.get("sec") or SECFindings(status="skipped"),
        news=final_state.get("news") or NewsFindings(status="skipped"),
        metrics=final_state.get("metrics") or MetricsFindings(status="skipped"),
        report=final_state.get("report")
        or ResearchReport(
            ticker=ticker.upper(),
            recommendation="Pending",
            justification="Graph did not produce a report.",
            company_overview="",
            financial_health="",
        ),
    )
