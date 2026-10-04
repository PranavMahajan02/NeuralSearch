import { apiJson } from "./http";

export async function startIndexing(priorityPlatform: string, platforms: string[]) {
  return apiJson("/index/", {
    method: "POST",
    json: { priority_platform: priorityPlatform, platforms },
    errorMessage: "Unable to start indexing.",
  });
}

export async function getIndexJobs() {
  return apiJson<any[]>("/index/jobs", { errorMessage: "Unable to fetch indexing jobs." });
}
