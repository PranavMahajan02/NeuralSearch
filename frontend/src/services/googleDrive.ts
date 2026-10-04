import { apiJson } from "./http";

export async function connectGoogleDrive() {
  return apiJson("/platforms/google-drive/connect", { errorMessage: "Unable to connect Google Drive." });
}

export async function getGoogleDriveStatus() {
  return apiJson<{ connected: boolean }>("/platforms/google-drive/status", {
    errorMessage: "Unable to get Google Drive status.",
  });
}

export async function disconnectGoogleDrive() {
  return apiJson("/platforms/google-drive/disconnect", {
    method: "POST",
    errorMessage: "Unable to disconnect Google Drive.",
  });
}
