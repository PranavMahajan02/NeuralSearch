import { Eye } from "lucide-react";

import type { SearchResult } from "../../api/types";
import { reasonLabel } from "../../lib/platforms";
import { PlatformBadge, TypeIcon } from "../common/Badges";
import { Spinner } from "../common/Spinner";

interface Props {
  matches: SearchResult[];
  /** The main results were empty: say so in the heading. */
  noConfidentResults: boolean;
  openingId: string | null;
  onOpen: (result: SearchResult) => void;
  onDetails: (result: SearchResult) => void;
}

/**
 * Low-confidence visual matches (API `possible_matches`): images/videos just below the
 * visual evidence threshold. Kept apart from the results and never counted in the total.
 */
export function PossibleMatches({ matches, noConfidentResults, openingId, onOpen, onDetails }: Props) {
  if (matches.length === 0) return null;

  return (
    <section
      aria-labelledby="possible-title"
      className="mx-auto max-w-3xl space-y-2 rounded-2xl border border-dashed border-slate-300 bg-slate-50/60 p-4 dark:border-slate-700 dark:bg-slate-900/40"
    >
      <h2
        id="possible-title"
        className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400"
      >
        <Eye aria-hidden="true" className="h-4 w-4" />
        {noConfidentResults ? "No confident matches — possible visual matches:" : "Possible visual matches"}
      </h2>
      <p className="text-[11px] text-slate-600 dark:text-slate-400">
        These look somewhat like your query but are below the confidence threshold.
      </p>
      <ul className="space-y-2">
        {matches.map((result) => (
          <li
            key={`${result.platform}:${result.source_id}`}
            className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5 dark:border-slate-800 dark:bg-slate-900"
          >
            <TypeIcon type={result.type} className="h-4 w-4 shrink-0" />
            <div className="min-w-0 flex-1">
              <button
                type="button"
                onClick={() => onDetails(result)}
                aria-label={`View details of ${result.file}`}
                className="block max-w-full truncate text-left text-xs font-semibold text-slate-800 hover:text-blue-700 dark:text-slate-200 dark:hover:text-blue-400"
              >
                {result.file}
              </button>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-200">
                  Low confidence
                </span>
                <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
                  {reasonLabel("visual", result.match.frame_time_s)}
                </span>
                <PlatformBadge platform={result.platform} />
              </div>
            </div>
            <button
              type="button"
              onClick={() => onOpen(result)}
              disabled={openingId === result.source_id}
              aria-label={`${result.platform === "local" ? "Download" : "Open"} ${result.file}`}
              className="flex shrink-0 items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-50 disabled:bg-slate-200 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              {openingId === result.source_id && <Spinner />}
              {result.platform === "local" ? "Download" : "Open"}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
