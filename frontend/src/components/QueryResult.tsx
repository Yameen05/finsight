import type { QueryResponse } from "../api/client";

interface Props {
  result: QueryResponse | null;
}

export function QueryResultPanel({ result }: Props) {
  if (!result) return null;

  return (
    <section className="mt-8 space-y-3">
      <h2 className="text-lg font-medium">Top matches</h2>
      {result.matches.length === 0 && (
        <p className="text-sm text-slate-400">No matches returned.</p>
      )}
      <ul className="space-y-3">
        {result.matches.map((m, i) => (
          <li
            key={`${m.accession}-${m.chunk_index}-${i}`}
            className="rounded-md border border-slate-800 bg-slate-900 p-4"
          >
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
              <span>
                {m.form} · {m.accession} · {m.filing_date}
              </span>
              <span className="rounded-full bg-emerald-900/40 px-2 py-0.5 text-emerald-300">
                score {m.score.toFixed(3)}
              </span>
            </div>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200">{m.text}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
