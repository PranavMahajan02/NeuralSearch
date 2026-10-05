import React, { useState } from "react";
import {
  cancelIndexJob,
  getIndexJobErrors,
  IndexJob,
  isActive,
  JobError,
  JobStatus,
} from "../services/index";

const PLATFORM_LABELS: Record<string, string> = {
  local: "Local Storage",
  google_drive: "Google Drive",
  github: "GitHub",
};

const STATUS_STYLES: Record<JobStatus, { label: string; className: string }> = {
  queued: { label: "Queued", className: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300" },
  running: { label: "Indexing", className: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300" },
  completed: { label: "Completed", className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" },
  completed_with_errors: {
    label: "Completed with errors",
    className: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  },
  failed: { label: "Failed", className: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300" },
  cancelled: { label: "Cancelled", className: "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400" },
};

interface Props {
  jobs: IndexJob[];
  /** Fetch jobs again right away (after cancel). */
  onChanged?: () => void;
}

/** Real job state from the backend: status, counters, errors, cancel. */
export default function IndexJobsPanel({ jobs, onChanged }: Props) {
  const [openErrors, setOpenErrors] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, JobError[]>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  if (jobs.length === 0) {
    return null;
  }

  const toggleErrors = async (job: IndexJob) => {
    if (openErrors === job.id) {
      setOpenErrors(null);
      return;
    }
    setOpenErrors(job.id);
    try {
      const data = await getIndexJobErrors(job.id);
      setErrors((prev) => ({ ...prev, [job.id]: data.errors }));
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const cancel = async (job: IndexJob) => {
    setBusy(job.id);
    setMessage(null);
    try {
      await cancelIndexJob(job.id);
      onChanged?.();
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-3" data-testid="index-jobs-panel">
      {message && (
        <div role="alert" className="rounded-xl bg-rose-50 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300 text-xs px-3 py-2">
          {message}
        </div>
      )}

      {jobs.map((job) => {
        const style = STATUS_STYLES[job.status] ?? STATUS_STYLES.queued;
        const hasErrors = job.failed_files > 0 || job.status === "failed";

        return (
          <div
            key={job.id}
            className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold">{PLATFORM_LABELS[job.platform] ?? job.platform}</span>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${style.className}`}>
                  {job.cancel_requested && job.status === "running" ? "Cancelling…" : style.label}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {hasErrors && (
                  <button
                    type="button"
                    onClick={() => void toggleErrors(job)}
                    className="text-xs font-semibold text-slate-600 dark:text-slate-300 hover:underline"
                  >
                    {openErrors === job.id ? "Hide errors" : "View errors"}
                  </button>
                )}
                {isActive(job) && !job.cancel_requested && (
                  <button
                    type="button"
                    disabled={busy === job.id}
                    onClick={() => void cancel(job)}
                    className="rounded-lg border border-rose-200 dark:border-rose-800 px-2.5 py-1 text-xs font-semibold text-rose-600 dark:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-900/30 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>

            {(job.status === "running" || job.total_files > 0) && (
              <div className="mt-3">
                <div className="h-1.5 w-full rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-blue-600 transition-all"
                    style={{ width: `${Math.min(100, job.progress)}%` }}
                  />
                </div>
                <div className="mt-1.5 text-[11px] text-slate-500 dark:text-slate-400">
                  {job.processed_files}/{job.total_files} files · {job.succeeded_files} indexed ·{" "}
                  {job.failed_files} failed · {job.skipped_files} skipped
                  {job.status === "running" && job.current_file ? ` · ${job.current_file}` : ""}
                </div>
              </div>
            )}

            {job.error_message && (
              <p className="mt-2 text-xs text-rose-600 dark:text-rose-300 break-words">{job.error_message}</p>
            )}

            {openErrors === job.id && (
              <ul className="mt-3 max-h-48 overflow-auto space-y-1 text-[11px]">
                {(errors[job.id] ?? []).length === 0 && (
                  <li className="text-slate-500">No per-file errors recorded.</li>
                )}
                {(errors[job.id] ?? []).map((item, index) => (
                  <li key={`${item.file}-${index}`} className="break-words">
                    <span className="font-semibold">{item.file}</span>
                    <span className="text-slate-500"> — {item.error}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}
