import { apiJson } from "./http";

type FoldersResponse = { status?: string; folders: string[] };

export async function getFolders() {
  return apiJson<FoldersResponse>("/platforms/local/folders", { errorMessage: "Unable to load folders." });
}

export async function addFolder(folder: string) {
  return apiJson<FoldersResponse>("/platforms/local/folders", {
    method: "POST",
    json: { folder },
    errorMessage: "Unable to add folder.",
  });
}

export async function removeFolder(folder: string) {
  return apiJson<FoldersResponse>("/platforms/local/folders", {
    method: "DELETE",
    json: { folder },
    errorMessage: "Unable to remove folder.",
  });
}

/** Indexes the registered local folders through the regular /index/ endpoint. */
export async function indexLocalStorage() {
  return apiJson("/index/", {
    method: "POST",
    json: { priority_platform: "local", platforms: ["local"] },
    errorMessage: "Indexing failed.",
  });
}

/**
 * Opens a native folder dialog on the machine running the backend.
 * Development only: in production the endpoint does not exist and the
 * folder path must be typed in.
 */
export async function pickFolder() {
  return apiJson<{ folder: string }>("/platforms/local/pick-folder", {
    method: "POST",
    errorMessage: "The folder picker is not available. Please type the folder path.",
  });
}
