import { CheckCircle2, Layers } from "lucide-react";

import { useConnectionCount, useJobs, useStats } from "../api/queries";
import { PLATFORMS, isActiveJob } from "../api/types";
import { Skeleton } from "../components/common/Spinner";
import { JobCard } from "../components/indexing/JobCard";
import { IndexingStatsPanel, SyncRoadmap, type RoadmapRow } from "../components/indexing/IndexingSidebar";
import { allIndexed, platformState, queuePosition } from "../lib/indexing";

/** "Indexing Operations Office": live jobs (left), stats + roadmap (right). Real data only. */
export function IndexingPage() {
  const jobs = useJobs();
  const stats = useStats();
  const { connected, supported } = useConnectionCount();

  if (jobs.isPending) {
    return (
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3" aria-busy="true">
        <Skeleton className="h-64 rounded-2xl md:col-span-2" />
        <Skeleton className="h-64 rounded-2xl" />
      </div>
    );
  }

  if (jobs.isError) {
    return (
      <p role="alert" className="text-sm text-rose-700 dark:text-rose-300">
        Could not load indexing jobs: {jobs.error.message}
      </p>
    );
  }

  const list = jobs.data;
  const jobOf = (platform: string) => list.find((job) => job.platform === platform);
  const rows = Object.fromEntries(
    PLATFORMS.map((platform) => {
      const job = jobOf(platform);
      const row: RoadmapRow = {
        state: platformState(!!stats.data?.platforms[platform]?.connected, job),
        progress: job?.progress ?? 0,
      };
      return [platform, row];
    }),
  );
  const anyActive = list.some(isActiveJob);
  const everythingIndexed = !anyActive && allIndexed(Object.values(rows).map((r) => r.state));

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
      <section
        aria-labelledby="ix-current"
        className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-xs md:col-span-2 dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="flex items-center justify-between">
          <h2
            id="ix-current"
            className="flex items-center gap-2 font-display text-lg font-bold text-slate-800 dark:text-slate-100"
          >
            <Layers aria-hidden="true" className="h-5 w-5 text-blue-600" />
            Current Processing Platform
          </h2>
          <span
            className={`rounded-full border px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-wider ${
              anyActive
                ? "animate-pulse border-blue-100 bg-blue-50 text-blue-700 dark:border-blue-900/50 dark:bg-blue-950/40 dark:text-blue-300"
                : "border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400"
            }`}
          >
            {anyActive ? "Active" : "Idle"}
          </span>
        </div>

        {everythingIndexed && (
          <div
            role="status"
            className="flex items-center gap-2 rounded-xl border border-emerald-100 bg-emerald-50 p-4 text-emerald-900 dark:border-emerald-800/80 dark:bg-emerald-950/40 dark:text-emerald-200"
          >
            <CheckCircle2 aria-hidden="true" className="h-5 w-5 shrink-0" />
            <p className="text-xs font-semibold">
              All platforms indexed. Every connected platform is searchable.
            </p>
          </div>
        )}

        {PLATFORMS.map((platform) => {
          const job = jobOf(platform);
          return (
            <JobCard
              key={platform}
              platform={platform}
              job={job}
              position={job ? queuePosition(list, job) : null}
            />
          );
        })}
      </section>

      <div className="space-y-6">
        <IndexingStatsPanel stats={stats.data} connected={connected} supported={supported} />
        <SyncRoadmap rows={rows} />
      </div>
    </div>
  );
}
