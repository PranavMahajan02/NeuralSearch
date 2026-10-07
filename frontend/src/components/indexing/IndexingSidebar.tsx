import type { DashboardStats } from "../../api/types";
import { PLATFORMS } from "../../api/types";
import { formatDateTime, formatRelative } from "../../lib/format";
import type { PlatformState } from "../../lib/indexing";
import { platformLabel } from "../../lib/platforms";
import { PlatformLogo } from "../common/Badges";

function Stat({
  label,
  value,
  tone = "text-white",
  title,
}: {
  label: string;
  value: string | number;
  tone?: string;
  title?: string;
}) {
  return (
    <div className="border-b border-slate-800 pb-3">
      <dt className="block text-[10px] font-normal text-slate-400">{label}</dt>
      <dd className={`mt-1 block font-display text-xl font-semibold ${tone}`} title={title}>
        {value}
      </dd>
    </div>
  );
}

/** The dark "CogniSeek Indexing Stats" panel: real numbers from /dashboard/stats. */
export function IndexingStatsPanel({
  stats,
  connected,
  supported,
}: {
  stats: DashboardStats | undefined;
  connected: number;
  supported: number;
}) {
  const last = stats?.last_indexed_at ?? null;

  return (
    <section
      aria-labelledby="ix-stats"
      className="rounded-2xl border border-slate-800 bg-slate-900 p-5 text-white shadow-lg"
    >
      <h2 id="ix-stats" className="mb-4 font-mono text-xs font-bold uppercase tracking-widest text-slate-400">
        CogniSeek Indexing Stats
      </h2>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-4">
        <Stat label="Connected Portals" value={`${connected} / ${supported}`} />
        <Stat label="Indexed Files" value={stats?.total_files ?? "—"} />
        <Stat label="Images Cataloged" value={stats?.images ?? "—"} tone="text-emerald-400" />
        <Stat label="Audio Files" value={stats?.audio ?? "—"} tone="text-amber-400" />
        <Stat label="Videos Cataloged" value={stats?.video ?? "—"} tone="text-purple-400" />
        <Stat
          label="Last Indexed"
          value={last ? formatRelative(last) : "Never"}
          tone="text-slate-200 text-base"
          title={last ? formatDateTime(last) : undefined}
        />
      </dl>
    </section>
  );
}

const STATE_CLASS: Record<PlatformState, string> = {
  not_connected:
    "text-slate-600 bg-slate-100 border-slate-200 dark:text-slate-400 dark:bg-slate-800 dark:border-slate-700",
  not_indexed:
    "text-slate-600 bg-slate-100 border-slate-200 dark:text-slate-400 dark:bg-slate-800 dark:border-slate-700",
  queued:
    "text-slate-700 bg-slate-100 border-slate-200 dark:text-slate-300 dark:bg-slate-800 dark:border-slate-700",
  indexing:
    "text-blue-700 bg-blue-50 border-blue-100 dark:text-blue-300 dark:bg-blue-950/40 dark:border-blue-900/50",
  ready:
    "text-emerald-700 bg-emerald-50 border-emerald-100 dark:text-emerald-300 dark:bg-emerald-950/40 dark:border-emerald-900/50",
  failed:
    "text-rose-700 bg-rose-50 border-rose-100 dark:text-rose-300 dark:bg-rose-950/40 dark:border-rose-900/50",
  cancelled:
    "text-slate-700 bg-slate-100 border-slate-200 dark:text-slate-300 dark:bg-slate-800 dark:border-slate-700",
};

export interface RoadmapRow {
  state: PlatformState;
  progress: number;
}

function stateLabel({ state, progress }: RoadmapRow): string {
  switch (state) {
    case "not_connected":
      return "Not connected";
    case "not_indexed":
      return "Not indexed";
    case "queued":
      return "Queued";
    case "indexing":
      return `Indexing ${progress}%`;
    case "ready":
      return "✓ Ready";
    case "failed":
      return "Failed";
    case "cancelled":
      return "Cancelled";
  }
}

/** One row per platform with its real state. */
export function SyncRoadmap({ rows }: { rows: Record<string, RoadmapRow> }) {
  return (
    <section
      aria-labelledby="ix-roadmap"
      className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900"
    >
      <h2 id="ix-roadmap" className="mb-4 font-display text-sm font-bold text-slate-800 dark:text-slate-100">
        Platform Sync Roadmap
      </h2>
      <ul className="space-y-3">
        {PLATFORMS.map((platform) => {
          const row = rows[platform];
          return (
            <li
              key={platform}
              className={`flex items-center justify-between rounded-xl border p-2.5 ${
                row.state === "indexing"
                  ? "border-blue-200 bg-blue-50/50 dark:border-blue-900/60 dark:bg-blue-950/20"
                  : "border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-950/40"
              }`}
            >
              <span className="flex min-w-0 items-center gap-2.5">
                <PlatformLogo platform={platform} className="h-4.5 w-4.5" />
                <span className="truncate text-xs font-semibold text-slate-800 dark:text-slate-200">
                  {platformLabel(platform)}
                </span>
              </span>
              <span
                className={`rounded-full border px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider ${STATE_CLASS[row.state]}`}
              >
                {stateLabel(row)}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
