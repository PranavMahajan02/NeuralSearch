import type { JobStatus } from "../../api/types";
import {
  PLATFORM_BADGE,
  PLATFORM_COLOR,
  PLATFORM_ICON,
  TYPE_COLOR,
  TYPE_ICON,
  platformLabel,
} from "../../lib/platforms";

export function PlatformLogo({ platform, className = "w-4 h-4" }: { platform: string; className?: string }) {
  const Icon = PLATFORM_ICON[platform] ?? PLATFORM_ICON.google_drive;
  return <Icon aria-hidden="true" className={`${className} ${PLATFORM_COLOR[platform] ?? ""}`} />;
}

export function PlatformBadge({ platform }: { platform: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${PLATFORM_BADGE[platform] ?? PLATFORM_BADGE.github}`}
    >
      <PlatformLogo platform={platform} className="h-2.5 w-2.5" />
      {platformLabel(platform)}
    </span>
  );
}

export function TypeIcon({ type, className = "h-4 w-4" }: { type: string; className?: string }) {
  const Icon = TYPE_ICON[type] ?? TYPE_ICON.document;

  return (
    <Icon
      aria-label={type}
      role="img"
      className={`${className} ${TYPE_COLOR[type] ?? TYPE_COLOR.document}`}
    />
  );
}

const STATUS_CLASS: Record<JobStatus, string> = {
  queued:
    "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
  running:
    "bg-blue-50 text-blue-700 border-blue-100 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-900/50",
  completed:
    "bg-emerald-50 text-emerald-700 border-emerald-100 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900/50",
  completed_with_errors:
    "bg-amber-50 text-amber-800 border-amber-100 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900/50",
  failed:
    "bg-rose-50 text-rose-700 border-rose-100 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-900/50",
  cancelled:
    "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
};

const STATUS_LABEL: Record<JobStatus, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  completed_with_errors: "Completed with errors",
  failed: "Failed",
  cancelled: "Cancelled",
};

export function JobStatusBadge({ status, suffix = "" }: { status: JobStatus; suffix?: string }) {
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-wider ${STATUS_CLASS[status]}`}
    >
      {STATUS_LABEL[status]}
      {suffix}
    </span>
  );
}
