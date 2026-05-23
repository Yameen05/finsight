import { useEffect, useState } from "react";
import { TickerInput } from "./components/TickerInput";
import { QueryResultPanel } from "./components/QueryResult";
import { ReportPanel } from "./components/ReportPanel";
import { api, type FilingForm, type QueryResponse, type ResearchResponse } from "./api/client";

export default function App() {
  const [ticker, setTicker] = useState("AAPL");
  const [form, setForm] = useState<FilingForm>("10-K");
  const [question, setQuestion] = useState("What are the principal risks?");
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [research, setResearch] = useState<ResearchResponse | null>(null);
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [apiUp, setApiUp] = useState<boolean | null>(null);

  useEffect(() => {
    api.health().then(setApiUp).catch(() => setApiUp(false));
  }, []);

  async function onIngest() {
    setBusy(true);
    setStatus(`Ingesting ${form} for ${ticker}...`);
    try {
      const out = await api.ingest(ticker, form);
      setStatus(`Indexed ${out.chunks_indexed} chunks · ${out.accession} (${out.filing_date})`);
    } catch (e) {
      setStatus(`Ingest failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function onQuery() {
    setBusy(true);
    setStatus("Querying...");
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

  async function onResearch() {
    setBusy(true);
    setStatus(`Running research pipeline for ${ticker}...`);
    setResearch(null);
    try {
      const out = await api.research(ticker);
      setResearch(out);
      setStatus(`Report ready · recommendation: ${out.report.recommendation}`);
    } catch (e) {
      setStatus(`Research failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight">FinSight</h1>
        <p className="text-sm text-slate-400">
          Multi-agent stock research · Phase 2 · API:{" "}
          <span className={apiUp ? "text-emerald-400" : "text-rose-400"}>
            {apiUp === null ? "checking..." : apiUp ? "online" : "offline"}
          </span>
        </p>
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
              onClick={onResearch}
              disabled={busy}
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
            >
              Run full research
            </button>
          </div>
        </div>

        {status && <p className="text-xs text-slate-400">{status}</p>}
      </section>

      <ReportPanel result={research} />
      <QueryResultPanel result={queryResult} />
    </main>
  );
}
