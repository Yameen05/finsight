import type { ResearchResponse } from "../api/client";

interface Props {
  result: ResearchResponse | null;
}

const recColors: Record<string, string> = {
  Buy: "bg-emerald-700 text-emerald-100",
  Hold: "bg-amber-700 text-amber-100",
  Sell: "bg-rose-700 text-rose-100",
  Pending: "bg-slate-700 text-slate-200",
};

const statusColors: Record<string, string> = {
  ok: "text-emerald-400",
  skipped: "text-amber-400",
  not_implemented: "text-slate-500",
  error: "text-rose-400",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`text-xs uppercase tracking-wide ${statusColors[status] ?? "text-slate-400"}`}>
      {status}
    </span>
  );
}

export function ReportPanel({ result }: Props) {
  if (!result) return null;
  const { report, sec, news, metrics } = result;

  return (
    <section className="mt-8 space-y-5">
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xl font-semibold">{report.ticker} — Research report</h2>
          <span
            className={`rounded-full px-3 py-1 text-sm font-semibold ${
              recColors[report.recommendation] ?? recColors.Pending
            }`}
          >
            {report.recommendation}
          </span>
        </div>
        <p className="text-sm leading-relaxed text-slate-200">{report.justification}</p>

        {report.company_overview && (
          <Section title="Company overview">{report.company_overview}</Section>
        )}
        {report.financial_health && (
          <Section title="Financial health">{report.financial_health}</Section>
        )}
        {report.key_risks.length > 0 && (
          <div className="mt-4">
            <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
              Key risks
            </h3>
            <ul className="list-inside list-disc space-y-1 text-sm text-slate-200">
              {report.key_risks.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        )}
        {report.news_summary && (
          <Section title="News summary">{report.news_summary}</Section>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <AgentCard title="SEC filings" status={sec.status} error={sec.error}>
          {sec.findings.length > 0 && (
            <ul className="space-y-2 text-xs text-slate-300">
              {sec.findings.map((f, i) => (
                <li key={i}>
                  <div className="font-medium text-slate-200">{f.question}</div>
                  <div className="text-slate-400">{f.answer}</div>
                </li>
              ))}
            </ul>
          )}
          {sec.accession && (
            <div className="mt-2 text-[10px] text-slate-500">accession {sec.accession}</div>
          )}
        </AgentCard>

        <AgentCard title="News & sentiment" status={news.status} error={news.error}>
          {news.summary && <p className="text-xs text-slate-300">{news.summary}</p>}
          {news.sentiment_score !== null && (
            <p className="mt-1 text-xs text-slate-400">score {news.sentiment_score.toFixed(2)}</p>
          )}
        </AgentCard>

        <AgentCard title="Financial metrics" status={metrics.status} error={metrics.error}>
          {metrics.revenue !== null && (
            <Metric label="Revenue (TTM)" value={`$${(metrics.revenue / 1e9).toFixed(1)}B`} />
          )}
          {metrics.eps !== null && <Metric label="EPS (TTM)" value={metrics.eps.toFixed(2)} />}
          {metrics.pe_ratio !== null && <Metric label="P/E" value={metrics.pe_ratio.toFixed(1)} />}
          {metrics.profit_margin !== null && (
            <Metric label="Profit margin" value={`${(metrics.profit_margin * 100).toFixed(1)}%`} />
          )}
          {metrics.debt_to_equity !== null && (
            <Metric label="Debt / equity" value={metrics.debt_to_equity.toFixed(1)} />
          )}
          {metrics.week_52_low !== null && metrics.week_52_high !== null && (
            <Metric
              label="52-week range"
              value={`$${metrics.week_52_low.toFixed(2)} – $${metrics.week_52_high.toFixed(2)}`}
            />
          )}
        </AgentCard>
      </div>
    </section>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-4">
      <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">{title}</h3>
      <p className="text-sm leading-relaxed text-slate-200">{children}</p>
    </div>
  );
}

function AgentCard({
  title,
  status,
  error,
  children,
}: {
  title: string;
  status: string;
  error: string | null;
  children?: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-medium">{title}</h3>
        <StatusBadge status={status} />
      </div>
      {error && <p className="mb-2 text-xs text-slate-500">{error}</p>}
      {children}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between text-xs">
      <span className="text-slate-400">{label}</span>
      <span className="font-medium text-slate-200">{value}</span>
    </div>
  );
}
