import type { Job } from "../../api/types";

/** Human names for the backend's indexing stages (app/core/timing.py), in pipeline order. */
const STAGE_LABELS: Record<string, string> = {
  download: "Download",
  extract_text: "Text extraction",
  pdf_render: "PDF page rendering",
  ocr: "OCR",
  audio_extract: "Audio extraction",
  whisper: "Speech-to-text",
  frame_extract: "Video frames",
  clip_image: "Image embeddings",
  minilm: "Text embeddings",
  qdrant_upsert: "Vector store",
  ledger: "Bookkeeping",
  model_wait: "Waiting for a model",
  other: "Other",
};

const MIN_SHARE = 0.005; // stages under 0.5% of the time are folded into "Other"

export interface StageRow {
  stage: string;
  label: string;
  seconds: number;
  share: number;
}

/** Stage rows, largest first; tiny stages are folded into "Other". */
export function stageRows(timings: Job["stage_timings"]): StageRow[] {
  const seconds = (timings?.seconds ?? {}) as Record<string, number>;
  const total = Object.values(seconds).reduce((sum, value) => sum + (Number(value) || 0), 0);
  if (total <= 0) return [];

  let other = 0;
  const rows: StageRow[] = [];
  for (const [stage, raw] of Object.entries(seconds)) {
    const value = Number(raw) || 0;
    if (stage === "other" || value / total < MIN_SHARE) other += value;
    else rows.push({ stage, label: STAGE_LABELS[stage] ?? stage, seconds: value, share: value / total });
  }
  if (other > 0) rows.push({ stage: "other", label: "Other", seconds: other, share: other / total });

  return rows.sort((a, b) => b.seconds - a.seconds);
}

function formatSeconds(value: number): string {
  if (value >= 60) return `${Math.floor(value / 60)} min ${Math.round(value % 60)} s`;
  return value >= 10 ? `${Math.round(value)} s` : `${value.toFixed(1)} s`;
}

/** "Where the time went": the latest job's time per indexing stage as a bar list. */
export function StageBreakdown({ timings }: { timings: Job["stage_timings"] }) {
  const rows = stageRows(timings);
  if (rows.length === 0) return null;
  const longest = rows[0].seconds;

  return (
    <details className="group rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900/60">
      <summary className="cursor-pointer text-xs font-semibold text-slate-700 dark:text-slate-200">
        Where the time went
      </summary>
      <ul aria-label="Time per indexing stage" className="mt-3 space-y-2">
        {rows.map((row) => (
          <li key={row.stage} className="grid grid-cols-[8.5rem_1fr_4.5rem] items-center gap-2 text-xs">
            <span className="truncate text-slate-700 dark:text-slate-300">{row.label}</span>
            <span className="h-2 rounded-full bg-slate-100 dark:bg-slate-800" aria-hidden="true">
              <span
                className="block h-2 rounded-full bg-blue-600 dark:bg-blue-500"
                style={{ width: `${Math.max(2, (row.seconds / longest) * 100)}%` }}
              />
            </span>
            <span className="text-right tabular-nums text-slate-600 dark:text-slate-400">
              {formatSeconds(row.seconds)}
              <span className="sr-only"> ({Math.round(row.share * 100)}%)</span>
            </span>
          </li>
        ))}
      </ul>
    </details>
  );
}
