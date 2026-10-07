import { useConnectionCount, useStats } from "../../api/queries";
import { formatDateTime, formatRelative } from "../../lib/format";
import { Skeleton } from "../common/Spinner";

function Stat({ label, value, title }: { label: string; value: string | number; title?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-600 dark:text-slate-400">
        {label}
      </dt>
      <dd className="mt-1 text-xl font-semibold" title={title}>
        {value}
      </dd>
    </div>
  );
}

/** Numbers straight from /dashboard/stats (the indexed_files ledger). */
export function StatsGrid() {
  const stats = useStats();
  const { connected, supported } = useConnectionCount();

  if (stats.isPending) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6" aria-busy="true">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-20" />
        ))}
      </div>
    );
  }

  if (stats.isError) {
    return (
      <p role="alert" className="text-sm text-rose-700 dark:text-rose-300">
        Could not load the index statistics: {stats.error.message}
      </p>
    );
  }

  const s = stats.data;
  const last = s.last_indexed_at ?? null;

  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      <Stat label="Indexed files" value={s.total_files} />
      <Stat label="Documents" value={s.documents} />
      <Stat label="Images" value={s.images} />
      <Stat label="Audio · Video" value={`${s.audio} · ${s.video}`} />
      <Stat label="Platforms connected" value={`${connected} / ${supported}`} />
      <Stat
        label="Last indexed"
        value={last ? formatRelative(last) : "Never"}
        title={last ? formatDateTime(last) : undefined}
      />
    </dl>
  );
}
