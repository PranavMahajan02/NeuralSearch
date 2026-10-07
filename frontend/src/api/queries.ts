// TanStack Query setup: one client, query keys scoped by user, shared queries.
import { QueryClient, useQuery } from "@tanstack/react-query";

import { useAuth } from "../auth/AuthContext";
import { ApiError } from "./client";
import * as api from "./endpoints";
import { isActiveJob } from "./types";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 10_000,
        refetchOnWindowFocus: false,
        // Retry only transient failures, never 4xx (validation, auth, not found).
        retry: (count, error) =>
          count < 2 && error instanceof ApiError && (error.isNetworkError || error.status >= 500),
      },
      mutations: { retry: false },
    },
  });
}

// Every key starts with ["user", <id>] so one user's data is never shown to the next.
export const keys = {
  user: (userId: string) => ["user", userId] as const,
  stats: (userId: string) => ["user", userId, "stats"] as const,
  recent: (userId: string) => ["user", userId, "recent"] as const,
  jobs: (userId: string) => ["user", userId, "jobs"] as const,
  jobErrors: (userId: string, jobId: string) => ["user", userId, "job-errors", jobId] as const,
  folders: (userId: string) => ["user", userId, "folders"] as const,
  drive: (userId: string) => ["user", userId, "drive-status"] as const,
  github: (userId: string) => ["user", userId, "github-status"] as const,
  search: (userId: string, query: string, type: string, platform: string) =>
    ["user", userId, "search", query, type, platform] as const,
  suggestions: (userId: string, prefix: string) => ["user", userId, "suggestions", prefix] as const,
};

export const JOBS_ACTIVE_POLL_MS = 2000;

/**
 * The ONE /index/jobs poller. Every component that needs jobs calls this hook;
 * TanStack Query shares the single request between them. It refetches every
 * 2 s while a job is queued or running and stops polling otherwise (mutations
 * that start a job invalidate the key, which restarts it).
 */
export function useJobs() {
  const { userId } = useAuth();

  return useQuery({
    queryKey: keys.jobs(userId),
    queryFn: ({ signal }) => api.getJobs(signal),
    refetchInterval: (query) => (query.state.data?.some(isActiveJob) ? JOBS_ACTIVE_POLL_MS : false),
  });
}

/** Dashboard stats: counts, last indexed time and THE connection count. */
export function useStats() {
  const { userId } = useAuth();

  return useQuery({ queryKey: keys.stats(userId), queryFn: ({ signal }) => api.getStats(signal) });
}

/** "2 / 3 connected": the only place the connection count is computed (by the backend). */
export function useConnectionCount(): { connected: number; supported: number; isLoading: boolean } {
  const stats = useStats();

  return {
    connected: stats.data?.connected_platforms ?? 0,
    supported: stats.data?.supported_platforms ?? 3,
    isLoading: stats.isLoading,
  };
}

export function useFolders() {
  const { userId } = useAuth();

  return useQuery({ queryKey: keys.folders(userId), queryFn: ({ signal }) => api.getFolders(signal) });
}

export function useDriveStatus() {
  const { userId } = useAuth();

  return useQuery({ queryKey: keys.drive(userId), queryFn: ({ signal }) => api.getDriveStatus(signal) });
}

export function useGithubStatus() {
  const { userId } = useAuth();

  return useQuery({ queryKey: keys.github(userId), queryFn: ({ signal }) => api.getGithubStatus(signal) });
}

/** Everything that changes after indexing starts or a connection changes. */
export function invalidateIndexState(client: QueryClient, userId: string): Promise<void> {
  return client.invalidateQueries({
    predicate: (query) =>
      query.queryKey[0] === "user" &&
      query.queryKey[1] === userId &&
      ["stats", "recent", "jobs", "folders", "drive-status", "github-status"].includes(
        String(query.queryKey[2]),
      ),
  });
}
