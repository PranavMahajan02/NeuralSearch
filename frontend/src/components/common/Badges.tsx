import type { JobStatus } from "../../api/types";
import { PLATFORM_BADGE, PLATFORM_ICON, TYPE_ICON, platformLabel } from "../../lib/platforms";

export function PlatformBadge({ platform }: { platform: string }) {
  const Icon = PLATFORM_ICON[platform];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${PLATFORM_BADGE[platform] ?? PLATFORM_BADGE.github}`}
    >
      {Icon && <Icon aria-hidden="true" className="h-3 w-3" />}
      {platformLabel(platform)}
    </span>
  );
}

export function TypeIcon({ type, className = "h-5 w-5" }: { type: string; className?: string }) {
  const Icon = TYPE_ICON[type] ?? TYPE_ICON.document;

  return <Icon aria-label={type} role="img" className={className} />;
}

const STATUS_CLASS: Record<JobStatus, string> = {
  queued: "bg-amber-50 text-amber-900 ring-amber-300 dark:bg-amber-950 dark:text-amber-200",
  running: "bg-blue-50 text-blue-900 ring-blue-300 dark:bg-blue-950 dark:text-blue-200",
  completed: "bg-emerald-50 text-emerald-900 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-200",
  completed_with_errors: "bg-amber-50 text-amber-900 ring-amber-300 dark:bg-amber-950 dark:text-amber-200",
  failed: "bg-rose-50 text-rose-900 ring-rose-300 dark:bg-rose-950 dark:text-rose-200",
  cancelled: "bg-slate-100 text-slate-800 ring-slate-300 dark:bg-slate-800 dark:text-slate-200",
};

const STATUS_LABEL: Record<JobStatus, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  completed_with_errors: "Completed with errors",
  failed: "Failed",
  cancelled: "Cancelled",
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${STATUS_CLASS[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}
