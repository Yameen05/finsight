# FinSight

A multi-agent financial research system. Enter a ticker, get a structured
research report (Buy / Hold / Sell) synthesized from SEC filings, news
sentiment, and financial metrics.

> **Phase 2 (current)** — LangGraph orchestrator wired up: a coordinator runs
> the SEC RAG agent (real), plus News and Metrics agents (stubs) in parallel,
> then a synthesizer node produces a structured report skeleton.
>
> Phase 1 delivered the SEC EDGAR → Pinecone RAG vertical slice. NewsAPI,
> yFinance, and the real Buy/Hold/Sell decision logic arrive in later phases.
> See **Roadmap** below.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn, httpx |
| Frontend | Vite + React 18 + TypeScript + Tailwind CSS |
| Embeddings | OpenAI `text-embedding-3-small` (1536 dims) |
| LLM | OpenAI `gpt-4o-mini` (used from Phase 2) |
| Vector DB | Pinecone serverless |
| Chunking | LangChain `RecursiveCharacterTextSplitter` |
| Orchestration | LangGraph (parallel fan-out + fan-in synthesizer) |
| Containerization | Docker Compose |

## Quickstart

### 1. Configure environment

```bash
cd ~/Documents/Projects/finsight
cp .env.example .env
```

Edit `.env` and set at minimum:

- `OPENAI_API_KEY` — your OpenAI key
- `PINECONE_API_KEY` — your Pinecone key
- `SEC_USER_AGENT` — `"FinSight Research <your.email>"` (**required by SEC**)

### 2. Start the stack

```bash
docker compose up --build
```

- Backend → http://localhost:8000 · OpenAPI docs at http://localhost:8000/docs
- Frontend → http://localhost:5173

### 3. Ingest a filing and query it

UI: open http://localhost:5173, type `AAPL`, click **Ingest** (takes ~30–60s for a full 10-K), type a question, click **Query**.

curl equivalent:

```bash
curl -X POST localhost:8000/filings/ingest \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"AAPL","form":"10-K"}'
# → {"ticker":"AAPL","form":"10-K","accession":"…","filing_date":"…","chunks_indexed":312}

curl -X POST localhost:8000/filings/query \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"AAPL","question":"What are the principal risks?","top_k":5}'
```

### 4. Run the full research pipeline

The LangGraph orchestrator runs the SEC RAG agent + News/Metrics stubs in
parallel and synthesizes a structured report. Requires the ticker's filing to
already be ingested.

```bash
curl -X POST localhost:8000/research/AAPL
# → {
#     "ticker": "AAPL",
#     "sec": { "status": "ok", "findings": [...], "accession": "..." },
#     "news": { "status": "not_implemented", ... },
#     "metrics": { "status": "not_implemented", ... },
#     "report": { "recommendation": "Pending", "justification": "...", ... }
#   }
```

Or click **Run full research** in the UI.

## Important: SEC User-Agent

The SEC EDGAR API blocks requests without a descriptive `User-Agent` header that
includes a contact email. Set `SEC_USER_AGENT` in `.env` before ingesting or
you'll get HTTP 403.

## Project Layout

```
finsight/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── app/
│       ├── main.py              FastAPI app + CORS
│       ├── config.py            pydantic-settings (.env loader)
│       ├── routers/
│       │   ├── health.py        GET  /health
│       │   ├── filings.py       POST /filings/ingest, /filings/query
│       │   └── research.py      POST /research/{ticker}  (Phase 2 stub)
│       ├── services/
│       │   ├── sec_client.py    SEC EDGAR fetcher (CIK lookup, 10-K/10-Q)
│       │   ├── chunker.py       RecursiveCharacterTextSplitter wrapper
│       │   ├── embeddings.py    OpenAI batch embedder
│       │   └── vectorstore.py   Pinecone serverless wrapper
│       ├── schemas/             Pydantic request/response models (filings, research)
│       ├── scripts/             CLI helpers (pinecone_init, fetch_sample)
│       ├── agents/              LangGraph orchestrator
│       │   ├── state.py         ResearchState TypedDict
│       │   ├── graph.py         StateGraph assembly + run_research()
│       │   └── nodes/           sec_agent (real), news/metrics (stub), synthesizer
│       └── tests/               pytest unit tests (incl. agent + graph)
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts           proxies /api → backend
│   └── src/
│       ├── App.tsx              Ticker input + ingest + query + results
│       ├── api/client.ts        Typed fetch wrappers
│       └── components/          TickerInput, QueryResult
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

## Development

`make help` lists all targets. Common ones:

```bash
make dev               # docker compose up --build
make logs              # tail container logs
make backend-test      # pytest inside backend/
make pinecone-init     # create the Pinecone index if it doesn't exist
make fetch-sample TICKER=AAPL   # sanity-check SEC fetch outside Docker
```

Backend code reloads on save (uvicorn `--reload`).  Frontend has Vite HMR.

## Roadmap

| Phase | Adds |
|---|---|
| 1 | Repo, FastAPI, React/TS, Docker, SEC→Pinecone→RAG query |
| **2 (now)** | LangGraph orchestrator; real SEC RAG agent; News/Metrics stubs; synthesizer; `/research/{ticker}` endpoint; UI report panel |
| 3 | News & Sentiment agent (NewsAPI) — replace stub |
| 4 | Financial Metrics agent (yFinance) — replace stub |
| 5 | Real Buy / Hold / Sell decision logic in synthesizer (all three signals) |
| 6 | Auth, persistence beyond Pinecone, production Dockerfile, CI |
