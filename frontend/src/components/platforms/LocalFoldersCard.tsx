import { Play } from "lucide-react";

import { useFolders } from "../../api/queries";
import type { JobWithHistory, PlatformDetail } from "../../api/types";
import { isActiveJob } from "../../api/types";
import { usePlatformActions } from "../../hooks/usePlatformActions";
import { formatDateTime, formatRelative } from "../../lib/format";
import { PlatformLogo } from "../common/Badges";
import { FolderManager } from "./FolderManager";

interface Props {
  detail: PlatformDetail | undefined;
  job: JobWithHistory | undefined;
}

export function LocalFoldersCard({ detail, job }: Props) {
  const { startIndexing } = usePlatformActions();
  const folders = useFolders();
  const count = folders.data?.folders.length ?? 0;
  const indexing = job ? isActiveJob(job) : false;

  return (
    <section
      aria-labelledby="local-title"
      className={`flex flex-col gap-4 rounded-xl border p-4 transition-all ${
        count > 0
          ? "border-blue-200 bg-slate-50/50 dark:border-blue-900/60 dark:bg-slate-950/40"
          : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3 dark:border-slate-800/60">
        <div className="flex items-center gap-3">
          <div className="rounded-lg border border-slate-100 bg-white p-2 dark:border-slate-800 dark:bg-slate-900">
            <PlatformLogo platform="local" className="h-6 w-6" />
          </div>
          <div>
            <h2 id="local-title" className="text-xs font-bold text-slate-800 dark:text-slate-100">
              Local Storage
            </h2>
            <span className="mt-0.5 block text-[10px] text-slate-500 dark:text-slate-400">
              {indexing ? "🟡 Indexing..." : count > 0 ? "🟢 Connected" : "⚪ Not Connected"} ·{" "}
              {detail?.indexed_files ?? 0} files · last indexed{" "}
              <span title={formatDateTime(detail?.last_indexed_at)}>
                {detail?.last_indexed_at ? formatRelative(detail.last_indexed_at) : "never"}
              </span>
            </span>
          </div>
        </div>
        <button
          type="button"
          disabled={count === 0 || indexing || startIndexing.isPending}
          onClick={() => startIndexing.mutate({ priority: "local", platforms: ["local"] })}
          className="flex items-center gap-1.5 rounded-xl bg-emerald-700 px-4 py-2 text-xs font-semibold text-white shadow-xs transition-all hover:bg-emerald-800 active:scale-97 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-700 dark:disabled:bg-slate-800 dark:disabled:text-slate-300"
        >
          <Play aria-hidden="true" className="h-3.5 w-3.5 fill-current" />
          {indexing ? "Indexing…" : "Index local folders"}
        </button>
      </div>
      <FolderManager />
    </section>
  );
}
