import { apiJson } from "./http";

export type JobStatus =
  | "queued"
  | "running"
  | "completed"
  | "completed_with_errors"
  | "failed"
  | "cancelled";

export type IndexJob = {
  id: string;
  platform: "local" | "google_drive" | "github";
  status: JobStatus;
  total_files: number;
  processed_files: number;
  succeeded_files: number;
  failed_files: number;
  skipped_files: number;
  /** Same as processed_files (kept for older code). */
  indexed_files: number;
  progress: number;
  current_file: string;
  error_message: string | null;
  cancel_requested: boolean;
  /** True once the platform has ever finished a run successfully. */
  indexed: boolean;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  heartbeat_at: string | null;
};

export type JobError = { file: string; error: string; created_at: string | null };

export const ACTIVE_STATUSES: JobStatus[] = ["queued", "running"];

export function isActive(job: IndexJob): boolean {
  return ACTIVE_STATUSES.includes(job.status);
}

export async function startIndexing(priorityPlatform: string, platforms: string[]) {
  return apiJson("/index/", {
    method: "POST",
    json: { priority_platform: priorityPlatform, platforms },
    errorMessage: "Unable to start indexing.",
  });
}

export async function getIndexJobs() {
  return apiJson<IndexJob[]>("/index/jobs", { errorMessage: "Unable to fetch indexing jobs." });
}

export async function cancelIndexJob(jobId: string) {
  return apiJson<IndexJob>(`/index/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST",
    errorMessage: "Unable to cancel indexing.",
  });
}

export async function getIndexJobErrors(jobId: string) {
  return apiJson<{ job_id: string; failed_files: number; errors: JobError[] }>(
    `/index/jobs/${encodeURIComponent(jobId)}/errors`,
    { errorMessage: "Unable to load indexing errors." }
  );
}
