import { FileText, FolderOpen, Image, Link2, Music, Video, type LucideIcon } from "lucide-react";

import { useConnectionCount, useStats } from "../../api/queries";
import { formatDateTime, formatRelative } from "../../lib/format";
import { Skeleton } from "../common/Spinner";

const TONE = {
  blue: "bg-blue-50 text-blue-600 dark:bg-blue-950/45 dark:text-blue-400",
  indigo: "bg-indigo-50 text-indigo-600 dark:bg-indigo-950/45 dark:text-indigo-400",
  emerald: "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/45 dark:text-emerald-400",
  amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/45 dark:text-amber-400",
  purple: "bg-purple-50 text-purple-600 dark:bg-purple-950/45 dark:text-purple-400",
  rose: "bg-rose-50 text-rose-600 dark:bg-rose-950/45 dark:text-rose-400",
};

function Stat({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string | number;
  icon: LucideIcon;
  tone: keyof typeof TONE;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-3xs transition-shadow hover:shadow-2xs dark:border-slate-800/80 dark:bg-slate-900">
      <div className="flex items-center gap-3">
        <div aria-hidden="true" className={`rounded-xl p-2.5 ${TONE[tone]}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <dt className="block text-[10px] font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {label}
          </dt>
          <dd className="mt-0.5 block font-mono text-xl font-bold text-slate-800 dark:text-white">{value}</dd>
        </div>
      </div>
    </div>
  );
}

/** "System Indexing Insights": real numbers from /dashboard/stats (the indexed_files ledger). */
export function StatsGrid() {
  const stats = useStats();
  const { connected, supported } = useConnectionCount();

  return (
    <section aria-labelledby="insights-title" className="space-y-4">
      <div className="flex items-baseline justify-between border-b border-slate-200 pb-2 dark:border-slate-800">
        <h2
          id="insights-title"
          className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400"
        >
          System Indexing Insights
        </h2>
        {stats.data && (
          <span
            className="text-[11px] text-slate-500 dark:text-slate-400"
            title={formatDateTime(stats.data.last_indexed_at)}
          >
            Last indexed: {stats.data.last_indexed_at ? formatRelative(stats.data.last_indexed_at) : "Never"}
          </span>
        )}
      </div>

      {stats.isPending ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3" aria-busy="true">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-20 rounded-2xl" />
          ))}
        </div>
      ) : stats.isError ? (
        <p role="alert" className="text-sm text-rose-700 dark:text-rose-300">
          Could not load the index statistics: {stats.error.message}
        </p>
      ) : (
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Stat label="Total Indexed" value={stats.data.total_files} icon={FileText} tone="blue" />
          <Stat label="Documents" value={stats.data.documents} icon={FolderOpen} tone="indigo" />
          <Stat label="Images" value={stats.data.images} icon={Image} tone="emerald" />
          <Stat label="Audio" value={stats.data.audio} icon={Music} tone="amber" />
          <Stat label="Video" value={stats.data.video} icon={Video} tone="purple" />
          <Stat label="Connected" value={`${connected} / ${supported}`} icon={Link2} tone="rose" />
        </dl>
      )}
    </section>
  );
}
