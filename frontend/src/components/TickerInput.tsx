import type { FilingForm } from "../api/client";

interface Props {
  ticker: string;
  setTicker: (t: string) => void;
  form: FilingForm;
  setForm: (f: FilingForm) => void;
  onIngest: () => void;
  disabled?: boolean;
}

export function TickerInput({ ticker, setTicker, form, setForm, onIngest, disabled }: Props) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <div className="flex-1">
        <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">
          Ticker
        </label>
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="AAPL"
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm uppercase focus:border-emerald-500 focus:outline-none"
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-400">
          Form
        </label>
        <select
          value={form}
          onChange={(e) => setForm(e.target.value as FilingForm)}
          className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none"
        >
          <option value="10-K">10-K</option>
          <option value="10-Q">10-Q</option>
        </select>
      </div>
      <button
        onClick={onIngest}
        disabled={disabled || !ticker}
        className="rounded-md bg-slate-700 px-4 py-2 text-sm font-medium hover:bg-slate-600 disabled:opacity-50"
      >
        Ingest
      </button>
    </div>
  );
}
