import { useQuery } from "@tanstack/react-query";
import { Clock, History } from "lucide-react";

import * as api from "../../api/endpoints";
import { keys } from "../../api/queries";
import { useAuth } from "../../auth/AuthContext";
import { useOpenFile } from "../../hooks/useOpenFile";
import { formatDateTime, formatRelative } from "../../lib/format";
import { PlatformBadge, TypeIcon } from "../common/Badges";
import { Skeleton } from "../common/Spinner";

interface RecentPanelProps {
  searches: string[];
  onSearch: (query: string) => void;
  onClearSearches: () => void;
}

function Panel({
  title,
  icon: Icon,
  action,
  children,
}: {
  title: string;
  icon: typeof Clock;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Icon aria-hidden="true" className="h-4 w-4" />
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

/** Real data only: the last files indexed (server) and the last searches (this browser). */
export function RecentPanel({ searches, onSearch, onClearSearches }: RecentPanelProps) {
  const { userId } = useAuth();
  const { open } = useOpenFile();
  const recent = useQuery({
    queryKey: keys.recent(userId),
    queryFn: ({ signal }) => api.getRecentFiles(signal),
  });

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Panel title="Recently indexed" icon={Clock}>
        {recent.isPending ? (
          <div className="space-y-2">
            <Skeleton className="h-4" />
            <Skeleton className="h-4" />
          </div>
        ) : recent.isError ? (
          <p className="text-sm text-rose-700 dark:text-rose-300">
            Could not load recent files: {recent.error.message}
          </p>
        ) : recent.data.files.length === 0 ? (
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Nothing indexed yet. Connect a platform and index it.
          </p>
        ) : (
          <ul className="space-y-1">
            {recent.data.files.map((file) => (
              <li key={`${file.platform}:${file.source_id}`}>
                <button
                  type="button"
                  onClick={() => void open(file)}
                  className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  <TypeIcon type={file.type} className="h-4 w-4 shrink-0 text-slate-500" />
                  <span className="min-w-0 flex-1 truncate">{file.file}</span>
                  <PlatformBadge platform={file.platform} />
                  <span
                    className="shrink-0 text-xs text-slate-600 dark:text-slate-400"
                    title={formatDateTime(file.indexed_at)}
                  >
                    {formatRelative(file.indexed_at)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel
        title="Recent searches"
        icon={History}
        action={
          searches.length > 0 && (
            <button
              type="button"
              onClick={onClearSearches}
              className="text-xs font-medium text-blue-800 hover:underline dark:text-blue-300"
            >
              Clear
            </button>
          )
        }
      >
        {searches.length === 0 ? (
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Your searches appear here (stored only in this browser).
          </p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {searches.map((query) => (
              <li key={query}>
                <button
                  type="button"
                  onClick={() => onSearch(query)}
                  className="rounded-full bg-slate-100 px-3 py-1 text-sm hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700"
                >
                  {query}
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
