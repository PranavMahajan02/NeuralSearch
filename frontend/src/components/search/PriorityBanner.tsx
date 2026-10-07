import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { CheckCircle2, RefreshCw } from "lucide-react";

import type { JobWithHistory } from "../../api/types";
import { isActiveJob } from "../../api/types";
import type { PriorityProgress } from "../../lib/indexing";
import { platformLabel } from "../../lib/platforms";

function progressText(job: JobWithHistory): string {
  if (job.status === "queued") return "queued";
  return job.total_files > 0 ? `${job.processed_files}/${job.total_files}` : "listing files";
}

/**
 * Shown while anything is queued or running. Search works the whole time:
 * files become searchable the moment they are indexed.
 */
export function PriorityBanner({ progress }: { progress: PriorityProgress }) {
  const { priority, others, priorityDone } = progress;
  const background = others.filter(isActiveJob);
  const done = background.reduce((n, j) => n + j.processed_files, 0);
  const total = background.reduce((n, j) => n + j.total_files, 0);

  return (
    <motion.div
      role="status"
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      className={`mx-auto flex max-w-3xl flex-wrap items-center gap-x-2 gap-y-1 rounded-2xl border px-4 py-3 text-xs ${
        priorityDone
          ? "border-emerald-100 bg-emerald-50 text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-200"
          : "border-blue-100 bg-blue-50 text-blue-900 dark:border-blue-900/50 dark:bg-blue-950/40 dark:text-blue-200"
      }`}
    >
      {priorityDone ? (
        <span className="flex items-center gap-1.5 font-semibold">
          <CheckCircle2 aria-hidden="true" className="h-4 w-4" />
          Searching {platformLabel(priority.platform)} ✓ ready
        </span>
      ) : (
        <span className="flex items-center gap-1.5 font-semibold">
          <RefreshCw aria-hidden="true" className="h-4 w-4 animate-spin" />
          {platformLabel(priority.platform)} indexing {progressText(priority)} — results may be incomplete
        </span>
      )}
      {background.length > 0 && (
        <span>
          · {background.map((j) => platformLabel(j.platform)).join(", ")} indexing in background
          {total > 0 ? ` (${done}/${total})` : ""}
        </span>
      )}
      <Link to="/indexing" className="ml-auto font-semibold underline underline-offset-2 hover:no-underline">
        Indexing Center
      </Link>
    </motion.div>
  );
}
