import { type ReactNode } from "react";

export type AgentKey = "sec_agent" | "news_agent" | "metrics_agent" | "synthesize";

export interface AgentState {
  status: "idle" | "running" | "done" | "error";
  summary?: string;
}

interface Props {
  states: Record<AgentKey, AgentState>;
}

const LABELS: Record<AgentKey, string> = {
  sec_agent: "SEC filings",
  news_agent: "News & sentiment",
  metrics_agent: "Financials",
  synthesize: "Synthesizer",
};

const DOT: Record<AgentState["status"], { color: string; pulse: boolean; label: string }> = {
  idle: { color: "bg-slate-700", pulse: false, label: "waiting" },
  running: { color: "bg-indigo-400", pulse: true, label: "running" },
  done: { color: "bg-emerald-500", pulse: false, label: "done" },
  error: { color: "bg-rose-500", pulse: false, label: "error" },
};

export function AgentProgress({ states }: Props) {
  return (
    <div className="grid gap-2 md:grid-cols-4">
      {(Object.keys(LABELS) as AgentKey[]).map((k) => {
        const s = states[k];
        const dot = DOT[s.status];
        return (
          <div
            key={k}
            className="flex items-center gap-3 rounded-md border border-slate-800 bg-slate-900/60 px-3 py-2"
          >
            <span
              className={`inline-block h-2.5 w-2.5 rounded-full ${dot.color} ${
                dot.pulse ? "animate-pulse" : ""
              }`}
              aria-label={dot.label}
            />
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-slate-200">{LABELS[k]}</div>
              <div className="truncate text-[11px] text-slate-500">{s.summary ?? dot.label}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function StatusLine({ children }: { children: ReactNode }) {
  return <p className="text-xs text-slate-400">{children}</p>;
}
