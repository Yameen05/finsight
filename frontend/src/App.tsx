import { useEffect, useRef, useState } from "react";
import { TickerInput } from "./components/TickerInput";
import { QueryResultPanel } from "./components/QueryResult";
import { ReportPanel } from "./components/ReportPanel";
import { AgentProgress, type AgentKey, type AgentState } from "./components/AgentProgress";
import { HistoryPanel } from "./components/HistoryPanel";
import {
  api,
  streamResearch,
  type FilingForm,
  type QueryResponse,
  type ResearchResponse,
  type ReadinessBody,
} from "./api/client";

type AgentStates = Record<AgentKey, AgentState>;

const INITIAL_AGENT_STATES: AgentStates = {
  sec_agent: { status: "idle" },
  news_agent: { status: "idle" },
  metrics_agent: { status: "idle" },
  synthesize: { status: "idle" },
};

export default function App() {
  const [ticker, setTicker] = useState("AAPL");
  const [form, setForm] = useState<FilingForm>("10-K");
  const [question, setQuestion] = useState("What are the principal risks?");
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [research, setResearch] = useState<ResearchResponse | null>(null);
  const [meta, setMeta] = useState<{ duration_ms: number; cost_usd: number } | null>(null);
  const [agents, setAgents] = useState<AgentStates>(INITIAL_AGENT_STATES);
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [readiness, setReadiness] = useState<ReadinessBody | null>(null);
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    api
      .ready()
      .then(({ body }) => setReadiness(body))
      .catch(() => setReadiness(null));
  }, []);

  function resetAgents() {
    setAgents({
      sec_agent: { status: "running" },
      news_agent: { status: "running" },
      metrics_agent: { status: "running" },
      synthesize: { status: "idle" },
    });
  }

  async function onIngest() {
    setBusy(true);
    setStatus(`Ingesting ${form} for ${ticker}…`);
    try {
      const out = await api.ingest(ticker, form);
      setStatus(
        `Indexed ${out.chunks_indexed} chunks · ${out.accession} (${out.filing_date})`,
      );
    } catch (e) {
      setStatus(`Ingest failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function onQuery() {
    setBusy(true);
    setStatus("Querying…");
    setQueryResult(null);
    try {
      const out = await api.query(ticker, question, 5);
      setQueryResult(out);
      setStatus(`Returned ${out.matches.length} chunks`);
    } catch (e) {
      setStatus(`Query failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function onResearchStream() {
    setBusy(true);
    setStatus(`Streaming research for ${ticker}…`);
    setResearch(null);
    setMeta(null);
    resetAgents();

    abortRef.current?.abort();
    const ctl = new AbortController();
    abortRef.current = ctl;

    try {
      await streamResearch(
        ticker,
        (e) => {
          if (e.event === "node_completed") {
            const node = e.data.node as AgentKey;
            const payload = e.data.payload;
            // Extract a 1-line summary from the payload's findings slot.
            let summary = "done";
            for (const k of ["sec", "news", "metrics", "report"]) {
              const v = (payload as Record<string, unknown>)[k] as Record<string, unknown> | undefined;
              if (v && typeof v === "object") {
                const stat = (v.status as string) ?? (v.recommendation as string);
                if (stat) summary = String(stat);
              }
            }
            setAgents((s) => ({ ...s, [node]: { status: "done", summary } }));
          } else if (e.event === "completed") {
            setResearch(e.data.result);
            setMeta({ duration_ms: e.data.duration_ms, cost_usd: e.data.cost.total_usd });
            setStatus(
              `Report ready · ${e.data.result.report.recommendation} · ${(e.data.duration_ms / 1000).toFixed(1)}s · $${e.data.cost.total_usd.toFixed(4)}`,
            );
            setHistoryRefresh((n) => n + 1);
          } else if (e.event === "error") {
            setStatus(`Research failed: ${e.data.detail}`);
          }
        },
        ctl.signal,
      );
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        setStatus(`Research failed: ${(e as Error).message}`);
      }
    } finally {
      setBusy(false);
    }
  }

  function onCancel() {
    abortRef.current?.abort();
    setBusy(false);
    setStatus("Cancelled");
  }

  const readinessSummary =
    readiness === null
      ? { color: "text-slate-400", text: "checking…" }
      : readiness.status === "ready"
      ? { color: "text-emerald-400", text: "all systems ready" }
      : {
          color: "text-amber-400",
          text:
            "degraded: " +
            Object.entries(readiness.checks)
              .filter(([, c]) => !c.ok)
              .map(([k]) => k)
              .join(", "),
        };

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <header className="mb-8 flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">FinSight</h1>
          <p className="text-sm text-slate-400">
            Multi-agent stock research · SEC RAG + News sentiment + yfinance
          </p>
        </div>
        <div className="text-right text-xs">
          <span className={readinessSummary.color}>● {readinessSummary.text}</span>
          {readiness && (
            <div className="mt-1 space-y-0.5 text-slate-500">
              {Object.entries(readiness.checks).map(([k, c]) => (
                <div key={k}>
                  <span className={c.ok ? "text-emerald-500" : "text-rose-500"}>
                    {c.ok ? "✓" : "✗"}
                  </span>{" "}
                  {k}
                </div>
              ))}
            </div>
          )}
        </div>
      </header>

      <section className="space-y-6 rounded-lg border border-slate-800 bg-slate-900 p-6">
        <TickerInput
          ticker={ticker}
          setTicker={setTicker}
          form={form}
          setForm={setForm}
          onIngest={onIngest}
          disabled={busy}
        />

        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">
            Ad-hoc question (single-agent RAG)
          </label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={2}
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={onQuery}
              disabled={busy}
              className="rounded-md bg-slate-700 px-4 py-2 text-sm font-medium hover:bg-slate-600 disabled:opacity-50"
            >
              Query
            </button>
            <button
              onClick={onResearchStream}
              disabled={busy}
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
            >
              Run full research (streaming)
            </button>
            {busy && (
              <button
                onClick={onCancel}
                className="rounded-md border border-rose-700 px-4 py-2 text-sm font-medium text-rose-300 hover:bg-rose-900/30"
              >
                Cancel
              </button>
            )}
          </div>
        </div>

        <AgentProgress states={agents} />

        {status && <p className="text-xs text-slate-400">{status}</p>}
        {meta && (
          <p className="text-[11px] text-slate-500">
            run · {(meta.duration_ms / 1000).toFixed(2)}s · ${meta.cost_usd.toFixed(4)}
          </p>
        )}
      </section>

      <ReportPanel result={research} />
      <QueryResultPanel result={queryResult} />

      <section className="mt-8">
        <h2 className="mb-2 text-sm font-medium text-slate-300">
          Recent reports for {ticker}
        </h2>
        <HistoryPanel ticker={ticker} refreshKey={historyRefresh} />
      </section>
    </main>
  );
}
