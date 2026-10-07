import { useMutation, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "../api/client";
import * as api from "../api/endpoints";
import { invalidateIndexState } from "../api/queries";
import type { PlatformName } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/common/Toast";
import { platformLabel } from "../lib/platforms";

function message(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

/** Mutations shared by the Platforms, Indexing and onboarding pages. */
export function usePlatformActions() {
  const { userId } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const refresh = () => invalidateIndexState(queryClient, userId);

  const startIndexing = useMutation({
    mutationFn: ({ priority, platforms }: { priority: PlatformName; platforms: PlatformName[] }) =>
      api.startIndexing(priority, platforms),
    onSuccess: (data) =>
      notify(`Indexing queued: ${data.platforms.map(platformLabel).join(", ")}.`, "success"),
    onError: (error) => notify(message(error, "Could not start indexing."), "error"),
    onSettled: refresh,
  });

  const connect = useMutation({
    mutationFn: (platform: api.CloudPlatform) => api.connectPlatform(platform),
    onSuccess: (data, platform) => {
      if (data.authorization_url) {
        window.location.assign(data.authorization_url); // the provider returns to /?<platform>=...
        return;
      }
      notify(`${platformLabel(platform)} is already connected.`, "info");
      void refresh();
    },
    onError: (error) => notify(message(error, "Could not start the connection."), "error"),
  });

  const disconnect = useMutation({
    mutationFn: ({ platform, purge }: { platform: api.CloudPlatform; purge: boolean }) =>
      api.disconnectPlatform(platform, purge),
    onSuccess: (data, { platform }) =>
      notify(
        `${platformLabel(platform)} disconnected${data.purged_files ? `; ${data.purged_files} indexed files removed` : ""}.`,
        "success",
      ),
    onError: (error) => notify(message(error, "Could not disconnect."), "error"),
    onSettled: refresh,
  });

  const cancelJob = useMutation({
    mutationFn: (jobId: string) => api.cancelJob(jobId),
    onSuccess: () => notify("Cancel requested. The job stops after the current file.", "info"),
    onError: (error) => notify(message(error, "Could not cancel the job."), "error"),
    onSettled: refresh,
  });

  const prioritize = useMutation({
    mutationFn: (jobId: string) => api.prioritizeJob(jobId),
    onSuccess: (job) => notify(`${platformLabel(job.platform)} will be indexed next.`, "success"),
    onError: (error) => notify(message(error, "Could not move the job."), "error"),
    onSettled: refresh,
  });

  return { startIndexing, connect, disconnect, cancelJob, prioritize };
}
