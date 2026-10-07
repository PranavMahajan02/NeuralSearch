import { motion } from "motion/react";

import type { SearchResult } from "../../api/types";
import { formatBytes, formatDate, relevance } from "../../lib/format";
import { reasonLabel } from "../../lib/platforms";
import { PlatformBadge, TypeIcon } from "../common/Badges";
import { Spinner } from "../common/Spinner";
import { Highlighted } from "./Highlighted";

const LEVEL_CLASS = {
  Strong:
    "bg-emerald-50 text-emerald-800 border-emerald-100 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900/40",
  Good: "bg-blue-50 text-blue-800 border-blue-100 dark:bg-blue-950/30 dark:text-blue-300 dark:border-blue-900/30",
  Partial:
    "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
};

export function RelevanceBadge({ score }: { score: number }) {
  const { level, percent } = relevance(score);

  return (
    <span
      title={`${level} match: relevance score ${percent}%`}
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold ${LEVEL_CLASS[level]}`}
    >
      {level} <span className="font-normal">· {percent}%</span>
    </span>
  );
}

export function ReasonChips({ reasons, frameTimeS }: { reasons: string[]; frameTimeS?: number | null }) {
  if (!reasons.length) return null;

  return (
    <ul aria-label="Why it matched" className="flex flex-wrap gap-1">
      {reasons.map((reason) => (
        <li
          key={reason}
          className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
        >
          {reasonLabel(reason, frameTimeS)}
        </li>
      ))}
    </ul>
  );
}

interface ResultCardProps {
  result: SearchResult;
  opening: boolean;
  onOpen: (result: SearchResult) => void;
  onDetails: (result: SearchResult) => void;
}

export function ResultCard({ result, opening, onOpen, onDetails }: ResultCardProps) {
  const { match } = result;
  const isDownload = result.platform === "local";
  const titleMatch = match.field === "filename";

  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="group relative flex flex-col rounded-2xl border border-slate-200 bg-white p-5 transition-all hover:border-blue-300 hover:shadow-xs dark:border-slate-800/85 dark:bg-slate-900 dark:hover:border-slate-700"
    >
      <div className="flex items-start gap-4">
        <div className="shrink-0 rounded-xl border border-slate-100 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-950">
          <TypeIcon type={result.type} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3 className="break-all pr-2 font-display text-sm font-bold text-slate-800 group-hover:text-blue-700 dark:text-slate-200 dark:group-hover:text-blue-400">
              {titleMatch ? <Highlighted text={result.file} ranges={match.highlights} /> : result.file}
            </h3>
            <RelevanceBadge score={result.score} />
          </div>
          <p className="mt-0.5 break-all font-mono text-[10px] text-slate-500 dark:text-slate-400">
            {result.display_path}
          </p>
          {!titleMatch && match.snippet && (
            <p className="mt-2 line-clamp-3 text-xs font-normal leading-relaxed text-slate-600 dark:text-slate-400">
              <Highlighted text={match.snippet} ranges={match.highlights} />
            </p>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 border-t border-slate-100 pt-3 text-[10px] font-medium text-slate-500 dark:border-slate-800 dark:text-slate-400">
        <PlatformBadge platform={result.platform} />
        <span aria-hidden="true">&bull;</span>
        <span>
          Size:{" "}
          <strong className="font-mono text-slate-700 dark:text-slate-300">
            {formatBytes(result.file_size)}
          </strong>
        </span>
        <span aria-hidden="true">&bull;</span>
        <span>
          Last Modified:{" "}
          <strong className="font-mono text-slate-700 dark:text-slate-300">
            {formatDate(result.modified_at)}
          </strong>
        </span>
        <span className="ml-auto">
          <ReasonChips reasons={match.reasons} frameTimeS={match.frame_time_s} />
        </span>
      </div>

      <div className="mt-4 flex items-center justify-end gap-2 border-t border-slate-100 pt-3 dark:border-slate-800/65">
        <button
          type="button"
          onClick={() => onDetails(result)}
          aria-label={`View details of ${result.file}`}
          className="cursor-pointer rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-700 transition-all hover:bg-slate-50 hover:text-slate-900 active:scale-97 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
        >
          View Details
        </button>
        <button
          type="button"
          onClick={() => onOpen(result)}
          disabled={opening}
          aria-label={`${isDownload ? "Download" : "Open"} ${result.file}`}
          className="flex cursor-pointer items-center gap-1.5 rounded-xl bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs transition-all hover:bg-blue-700 active:scale-97 disabled:bg-slate-200 disabled:text-slate-700"
        >
          {opening && <Spinner />}
          {isDownload ? "Download File" : "Open File"}
        </button>
      </div>
    </motion.article>
  );
}
