import { ExternalLink, Download } from "lucide-react";

import type { SearchResult } from "../../api/types";
import { formatBytes, formatDate, relevance } from "../../lib/format";
import { REASON_LABEL } from "../../lib/platforms";
import { PlatformBadge, TypeIcon } from "../common/Badges";
import { Spinner } from "../common/Spinner";
import { Highlighted } from "./Highlighted";

const LEVEL_CLASS = {
  Strong: "bg-emerald-50 text-emerald-900 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-200",
  Good: "bg-amber-50 text-amber-900 ring-amber-300 dark:bg-amber-950 dark:text-amber-200",
  Partial: "bg-slate-100 text-slate-800 ring-slate-300 dark:bg-slate-800 dark:text-slate-200",
};

export function RelevanceBadge({ score }: { score: number }) {
  const { level, percent } = relevance(score);

  return (
    <span
      title={`${level} match: relevance score ${percent}%`}
      className={`rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${LEVEL_CLASS[level]}`}
    >
      {level} <span className="font-normal">· {percent}%</span>
    </span>
  );
}

export function ReasonChips({ reasons }: { reasons: string[] }) {
  if (!reasons.length) return null;

  return (
    <ul aria-label="Why it matched" className="flex flex-wrap gap-1">
      {reasons.map((reason) => (
        <li
          key={reason}
          className="rounded-md bg-blue-50 px-1.5 py-0.5 text-xs font-medium text-blue-900 dark:bg-blue-950 dark:text-blue-200"
        >
          {REASON_LABEL[reason] ?? reason}
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
  const showSnippet = match.field !== "filename" && match.snippet;

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start gap-3">
        <TypeIcon type={result.type} className="mt-0.5 h-5 w-5 shrink-0 text-slate-600 dark:text-slate-300" />
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="min-w-0 text-base font-semibold">
              <button
                type="button"
                onClick={() => onDetails(result)}
                className="break-all text-left text-blue-800 hover:underline dark:text-blue-300"
              >
                {match.field === "filename" ? (
                  <Highlighted text={result.file} ranges={match.highlights} />
                ) : (
                  result.file
                )}
              </button>
            </h3>
            <RelevanceBadge score={result.score} />
          </div>
          <p className="break-all text-xs text-slate-600 dark:text-slate-400">{result.display_path}</p>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-600 dark:text-slate-400">
            <PlatformBadge platform={result.platform} />
            <span>{formatBytes(result.file_size)}</span>
            <span>Modified {formatDate(result.modified_at)}</span>
          </div>
          {showSnippet && (
            <p className="line-clamp-3 text-sm text-slate-700 dark:text-slate-300">
              <Highlighted text={match.snippet} ranges={match.highlights} />
            </p>
          )}
          <ReasonChips reasons={match.reasons} />
        </div>
        <button
          type="button"
          onClick={() => onOpen(result)}
          disabled={opening}
          aria-label={`${isDownload ? "Download" : "Open"} ${result.file}`}
          className="shrink-0 rounded-lg p-2 text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 dark:text-slate-200 dark:ring-slate-700 dark:hover:bg-slate-800"
        >
          {opening ? (
            <Spinner />
          ) : isDownload ? (
            <Download aria-hidden="true" className="h-4 w-4" />
          ) : (
            <ExternalLink aria-hidden="true" className="h-4 w-4" />
          )}
        </button>
      </div>
    </article>
  );
}
