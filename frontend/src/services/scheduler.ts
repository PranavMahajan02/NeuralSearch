import { apiJson } from "./http";

export type PlatformName = "local" | "google_drive" | "github";

export type SchedulerStatus = {
  current_platform: PlatformName | null;
  completed_platforms: PlatformName[];
  queue: PlatformName[];
  worker_running: boolean;
  priority_platform: PlatformName | null;
  priority_completed: boolean;
};

export async function startScheduler(priorityPlatform: PlatformName, platforms: PlatformName[]) {
  return apiJson<{ message: string }>("/scheduler/start", {
    method: "POST",
    json: { priority_platform: priorityPlatform, platforms },
    errorMessage: "Unable to start the scheduler.",
  });
}

export async function getSchedulerStatus() {
  return apiJson<SchedulerStatus>("/scheduler/status", {
    errorMessage: "Unable to load scheduler status.",
  });
}
