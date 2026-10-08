// Derived indexing state, computed from /index/jobs only (pure functions, unit-tested).
import type { JobWithHistory } from "../api/types";
import { isActiveJob } from "../api/types";
import { parseDate } from "./format";

const time = (value: string | null | undefined) => parseDate(value)?.getTime() ?? 0;

/** The worker's claim order: higher priority first, then oldest. */
export function claimOrder(a: JobWithHistory, b: JobWithHistory): number {
  return (b.priority ?? 0) - (a.priority ?? 0) || time(a.created_at) - time(b.created_at);
}

/** 1-based position of a queued job in the user's queue, or null. */
export function queuePosition(jobs: JobWithHistory[], job: JobWithHistory): number | null {
  if (job.status !== "queued") return null;
  const queued = jobs.filter((j) => j.status === "queued").sort(claimOrder);
  return queued.findIndex((j) => j.id === job.id) + 1 || null;
}

export interface PriorityProgress {
  priority: JobWithHistory;
  others: JobWithHistory[];
  /** The priority platform finished (searchable); others may still run. */
  priorityDone: boolean;
}

/** Jobs started together (one "Start indexing") are created within this window. */
const BATCH_WINDOW_MS = 2 * 60 * 1000;

/**
 * The priority-indexing picture while anything is queued or running:
 * the batch is every latest job created up to 2 minutes before the oldest
 * active job; its first job in claim order is the priority platform.
 * Null when nothing is active (the banner disappears).
 */
export function priorityProgress(jobs: JobWithHistory[]): PriorityProgress | null {
  const active = jobs.filter(isActiveJob);
  if (active.length === 0) return null;

  const batchStart = Math.min(...active.map((j) => time(j.created_at))) - BATCH_WINDOW_MS;
  const batch = jobs.filter((j) => time(j.created_at) >= batchStart).sort(claimOrder);
  const [priority, ...others] = batch.length ? batch : active;

  return {
    priority,
    others,
    priorityDone: priority.status === "completed" || priority.status === "completed_with_errors",
  };
}

export type PlatformState =
  "not_connected" | "queued" | "indexing" | "ready" | "failed" | "cancelled" | "not_indexed";

/** One row of the "Platform Sync Roadmap". */
export function platformState(connected: boolean, job: JobWithHistory | undefined): PlatformState {
  if (job?.status === "running") return "indexing";
  if (job?.status === "queued") return "queued";
  if (!connected) return "not_connected";
  if (!job) return "not_indexed";
  if (job.status === "failed") return "failed";
  if (job.status === "cancelled") return job.indexed ? "ready" : "cancelled";
  return "ready";
}

/** True only when every connected platform's latest job finished. */
export function allIndexed(states: PlatformState[]): boolean {
  const connected = states.filter((s) => s !== "not_connected");
  return connected.length > 0 && connected.every((s) => s === "ready");
}
