export type FilingForm = "10-K" | "10-Q";

export interface IngestResponse {
  ticker: string;
  form: FilingForm;
  accession: string;
  filing_date: string;
  chunks_indexed: number;
}

export interface QueryMatch {
  score: number;
  text: string;
  accession: string;
  form: FilingForm;
  filing_date: string;
  chunk_index: number;
}

export interface QueryResponse {
  ticker: string;
  question: string;
  matches: QueryMatch[];
}

export type AgentStatus = "ok" | "skipped" | "not_implemented" | "error";

export interface SECFinding {
  question: string;
  answer: string;
  source_chunks: number;
}

export interface SECFindings {
  status: AgentStatus;
  findings: SECFinding[];
  accession: string | null;
  error: string | null;
}

export interface NewsFindings {
  status: AgentStatus;
  sentiment_score: number | null;
  summary: string | null;
  article_count: number;
  error: string | null;
}

export interface MetricsFindings {
  status: AgentStatus;
  revenue: number | null;
  eps: number | null;
  pe_ratio: number | null;
  profit_margin: number | null;
  debt_to_equity: number | null;
  week_52_low: number | null;
  week_52_high: number | null;
  error: string | null;
}

export interface ResearchReport {
  ticker: string;
  recommendation: "Buy" | "Hold" | "Sell" | "Pending";
  justification: string;
  company_overview: string;
  financial_health: string;
  key_risks: string[];
  news_summary: string | null;
}

export interface ResearchResponse {
  ticker: string;
  sec: SECFindings;
  news: NewsFindings;
  metrics: MetricsFindings;
  report: ResearchReport;
}

const BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return (await res.json()) as T;
}

export const api = {
  health: async () => {
    const res = await fetch(`${BASE_URL}/health`);
    return res.ok;
  },

  ingest: (ticker: string, form: FilingForm) =>
    postJson<IngestResponse>("/filings/ingest", { ticker, form }),

  query: (ticker: string, question: string, top_k = 5) =>
    postJson<QueryResponse>("/filings/query", { ticker, question, top_k }),

  research: async (ticker: string): Promise<ResearchResponse> => {
    const res = await fetch(`${BASE_URL}/research/${encodeURIComponent(ticker)}`, {
      method: "POST",
    });
    if (!res.ok) {
      throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
    }
    return (await res.json()) as ResearchResponse;
  },
};
