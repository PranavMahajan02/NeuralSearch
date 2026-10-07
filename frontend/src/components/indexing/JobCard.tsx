import { useState } from "react";

import type { Job, JobWithHistory, PlatformName } from "../../api/types";
import { isActiveJob } from "../../api/types";
import { usePlatformActions } from "../../hooks/usePlatformActions";
import { formatDateTime, formatDuration } from "../../lib/format";
import { PLATFORM_ICON, platformLabel } from "../../lib/platforms";
import { JobStatusBadge } from "../common/Badges";
import { Button } from "../common/Button";
import { JobErrors } from "./JobErrors";

function Counter({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <dt className="text-xs text-slate-600 dark:text-slate-400">{label}</dt>
      <dd className="text-lg font-semibold">{value}</dd>
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
        className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
      >
        <div
          className={`h-full bg-blue-700 transition-[width] ${known ? "" : "w-1/3 animate-pulse"}`}
          style={known ? { width: `${job.progress}%` } : undefined}
        />
      </div>
      <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
        {known ? `${job.processed_files} of ${job.total_files} files (${job.progress}%)` : "Listing files…"}
      </p>
    </div>
  );
}

function History({ jobs }: { jobs: Job[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">Recent runs</caption>
        <thead className="text-xs text-slate-600 dark:text-slate-400">
          <tr>
            <th scope="col" className="py-1 pr-3 font-medium">
              Started
            </th>
            <th scope="col" className="py-1 pr-3 font-medium">
              Status
            </th>
            <th scope="col" className="py-1 pr-3 font-medium">
              Indexed
            </th>
            <th scope="col" className="py-1 pr-3 font-medium">
              Failed
            </th>
            <th scope="col" className="py-1 pr-3 font-medium">
              Skipped
            </th>
            <th scope="col" className="py-1 font-medium">
              Duration
            </th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className="border-t border-slate-200 dark:border-slate-800">
              <td className="py-1.5 pr-3 whitespace-nowrap">
                {formatDateTime(job.started_at ?? job.created_at)}
              </td>
              <td className="py-1.5 pr-3">
                <JobStatusBadge status={job.status} />
              </td>
              <td className="py-1.5 pr-3">{job.succeeded_files}</td>
              <td className="py-1.5 pr-3">{job.failed_files}</td>
              <td className="py-1.5 pr-3">{job.skipped_files}</td>
              <td className="py-1.5 whitespace-nowrap">{formatDuration(job.started_at, job.completed_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function JobCard({ platform, job }: { platform: PlatformName; job: JobWithHistory | undefined }) {
  const { cancelJob } = usePlatformActions();
  const [showErrors, setShowErrors] = useState(false);
  const Icon = PLATFORM_ICON[platform];
  const active = job ? isActiveJob(job) : false;

  return (
    <section
      aria-labelledby={`job-${platform}`}
      className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex flex-wrap items-center gap-3">
        <Icon aria-hidden="true" className="h-5 w-5" />
        <h2 id={`job-${platform}`} className="flex-1 text-base font-semibold">
          {platformLabel(platform)}
        </h2>
        {job && <JobStatusBadge status={job.status} />}
        {job && active && (
          <Button
            variant="danger"
            disabled={job.cancel_requested || cancelJob.isPending}
            onClick={() => cancelJob.mutate(job.id)}
          >
            {job.cancel_requested ? "Cancelling…" : "Cancel"}
          </Button>
        )}
      </div>

      {!job ? (
        <p className="text-sm text-slate-600 dark:text-slate-400">Never indexed.</p>
      ) : (
        <>
          {job.status === "running" && <ProgressBar job={job} />}
          {job.status === "running" && job.current_file && (
            <p className="break-all text-sm text-slate-700 dark:text-slate-300">
              <span className="font-medium">Current file:</span> {job.current_file}
            </p>
          )}
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Counter label="Indexed" value={job.succeeded_files} />
            <Counter label="Failed" value={job.failed_files} />
            <Counter label="Skipped" value={job.skipped_files} />
            <Counter label="Downloaded" value={job.downloaded_files} />
            <div>
              <dt className="text-xs text-slate-600 dark:text-slate-400">Duration</dt>
              <dd className="text-lg font-semibold">{formatDuration(job.started_at, job.completed_at)}</dd>
            </div>
          </dl>
          {job.error_message && (
            <p
              role="alert"
              className="rounded-lg bg-rose-50 p-3 text-sm text-rose-950 dark:bg-rose-950 dark:text-rose-100"
            >
              {job.error_message}
            </p>
          )}
          {job.failed_files > 0 && (
            <div className="space-y-2">
              <Button variant="ghost" aria-expanded={showErrors} onClick={() => setShowErrors((v) => !v)}>
                {showErrors ? "Hide" : "Show"} {job.failed_files} file error
                {job.failed_files === 1 ? "" : "s"}
              </Button>
              {showErrors && <JobErrors jobId={job.id} />}
            </div>
          )}
          {job.history && job.history.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer font-medium">
                {job.history.length === 1 ? "Last run" : `Last ${job.history.length} runs`}
              </summary>
              <div className="mt-2">
                <History jobs={job.history} />
              </div>
            </details>
          )}
        </>
      )}
    </section>
  );
}
