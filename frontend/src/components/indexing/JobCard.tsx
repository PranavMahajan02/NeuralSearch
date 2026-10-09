import { useState } from "react";
import { motion } from "motion/react";

import type { Job, JobWithHistory, PlatformName } from "../../api/types";
import { isActiveJob } from "../../api/types";
import { usePlatformActions } from "../../hooks/usePlatformActions";
import { formatDuration } from "../../lib/format";
import { platformLabel } from "../../lib/platforms";
import { JobStatusBadge, PlatformLogo } from "../common/Badges";
import { JobErrors } from "./JobErrors";
import { JobHistory } from "./JobHistory";
import { StageBreakdown } from "./StageBreakdown";

function Counter({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <dt className="text-[10px] text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="font-mono text-base font-semibold text-slate-800 dark:text-slate-100">{value}</dd>
    </div>
  );
}

function ProgressBar({ job }: { job: Job }) {
  const known = job.total_files > 0;

  return (
    <div>
      <div
        role="progressbar"
        aria-label={`${platformLabel(job.platform)} indexing progress`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={known ? job.progress : undefined}
        aria-valuetext={known ? `${job.processed_files} of ${job.total_files} files` : "Listing files"}
        className="h-3 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"
      >
        <motion.div
          className={`h-full rounded-full bg-blue-600 ${known ? "" : "w-1/3 animate-pulse"}`}
          animate={known ? { width: `${job.progress}%` } : undefined}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
      </div>
      <p className="mt-2 text-sm font-medium text-slate-700 dark:text-slate-300">
        {known ? `${job.processed_files} of ${job.total_files} files (${job.progress}%)` : "Listing files…"}
      </p>
    </div>
  );
}

const SMALL =
  "cursor-pointer rounded-lg px-3 py-1 text-[10px] font-bold uppercase tracking-wider transition-all";

interface Props {
  platform: PlatformName;
  job: JobWithHistory | undefined;
  /** 1-based queue position when the job is queued. */
  position: number | null;
}

export function JobCard({ platform, job, position }: Props) {
  const { cancelJob, prioritize } = usePlatformActions();
  const [showErrors, setShowErrors] = useState(false);
  const active = job ? isActiveJob(job) : false;

  return (
    <section
      aria-labelledby={`job-${platform}`}
      className={`space-y-4 rounded-xl border p-4 ${
        job?.status === "running"
          ? "border-blue-200 bg-blue-50/40 dark:border-blue-900/60 dark:bg-blue-950/20"
          : "border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-950/40"
      }`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <PlatformLogo platform={platform} className="h-8 w-8" />
        <div className="min-w-0 flex-1">
          <h3
            id={`job-${platform}`}
            className="font-display text-base font-bold text-slate-800 dark:text-slate-100"
          >
            {platformLabel(platform)}
          </h3>
          <p className="truncate text-xs text-slate-500 dark:text-slate-400">
            {!job ? "Never indexed." : job.status === "running" ? "Scanning, extracting and indexing…" : null}
          </p>
        </div>
        {job && <JobStatusBadge status={job.status} suffix={position ? ` (#${position})` : ""} />}
        {job?.status === "queued" && position !== null && position > 1 && (
          <button
            type="button"
            disabled={prioritize.isPending}
            onClick={() => prioritize.mutate(job.id)}
            className={`${SMALL} bg-blue-600 text-white hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-700`}
          >
            Index next
          </button>
        )}
        {job && active && (
          <button
            type="button"
            disabled={job.cancel_requested || cancelJob.isPending}
            onClick={() => cancelJob.mutate(job.id)}
            className={`${SMALL} bg-rose-50 text-rose-700 hover:bg-rose-100 disabled:bg-slate-200 disabled:text-slate-700 dark:bg-rose-950/30 dark:text-rose-300`}
          >
            {job.cancel_requested ? "Cancelling…" : "Cancel"}
          </button>
        )}
      </div>

      {job && (
        <>
          {job.status === "running" && <ProgressBar job={job} />}
          {job.status === "running" && job.current_file && (
            <p className="break-all text-xs text-slate-600 dark:text-slate-400">
              Current file: {job.current_file}
            </p>
          )}
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Counter label="Indexed" value={job.succeeded_files} />
            <Counter label="Failed" value={job.failed_files} />
            <Counter label="Skipped" value={job.skipped_files} />
            <Counter label="Downloaded" value={job.downloaded_files} />
            <Counter label="Duration" value={formatDuration(job.started_at, job.completed_at)} />
          </dl>
          {job.error_message && (
            <p
              role="alert"
              className="rounded-lg border border-rose-100 bg-rose-50 p-3 text-xs text-rose-900 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-100"
            >
              {job.error_message}
            </p>
          )}
          {job.failed_files > 0 && (
            <div className="space-y-2">
              <button
                type="button"
                aria-expanded={showErrors}
                onClick={() => setShowErrors((v) => !v)}
                className="text-xs font-semibold text-blue-700 hover:underline dark:text-blue-400"
              >
                {showErrors ? "Hide errors" : `View errors (${job.failed_files})`}
              </button>
              {showErrors && <JobErrors jobId={job.id} />}
            </div>
          )}
          {!active && <StageBreakdown timings={job.stage_timings} />}
          <JobHistory jobs={job.history ?? []} />
        </>
      )}
    </section>
  );
}
