import { apiJson } from "./http";

type ConnectResponse = {
  status: string;
  connected: boolean;
  account_email?: string | null;
  message?: string;
  authorization_url?: string;
};

/**
 * Starts Google's web OAuth flow: if Drive is not connected yet the browser
 * goes to Google, and the backend callback brings it back to
 * FRONTEND_URL/?google_drive=connected (or ?google_drive=error&reason=...).
 */
export async function connectGoogleDrive(): Promise<ConnectResponse> {
  const data = await apiJson<ConnectResponse>("/platforms/google-drive/connect", {
    errorMessage: "Unable to connect Google Drive.",
  });

  if (!data.connected && data.authorization_url) {
    window.location.assign(data.authorization_url);
  }

  return data;
}

export async function getGoogleDriveStatus() {
  return apiJson<{ connected: boolean; account_email?: string | null }>("/platforms/google-drive/status", {
    errorMessage: "Unable to get Google Drive status.",
  });
}

/** purge=true also deletes everything indexed from Drive. */
export async function disconnectGoogleDrive(purge = false) {
  return apiJson(`/platforms/google-drive/disconnect${purge ? "?purge=true" : ""}`, {
    method: "POST",
    errorMessage: "Unable to disconnect Google Drive.",
  });
}
