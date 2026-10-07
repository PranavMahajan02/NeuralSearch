import { apiJson } from "./http";

type ConnectResponse = {
  status: string;
  connected: boolean;
  username?: string;
  message?: string;
  authorization_url?: string;
};

/**
 * Starts the GitHub OAuth flow. If GitHub is not connected yet, the browser
 * is redirected to GitHub; the backend callback then sends it back to
 * FRONTEND_URL/?github=connected (or ?github=error&reason=...).
 */
export async function connectGithub(): Promise<ConnectResponse> {
  const data = await apiJson<ConnectResponse>("/platforms/github/connect", {
    errorMessage: "Unable to connect GitHub.",
  });

  if (!data.connected && data.authorization_url) {
    window.location.assign(data.authorization_url);
  }

  return data;
}

export async function getGithubStatus() {
  return apiJson<{ connected: boolean; account_name?: string | null }>("/platforms/github/status", {
    errorMessage: "Unable to fetch GitHub status.",
  });
}

/** purge=true also deletes everything indexed from GitHub. */
export async function disconnectGithub(purge = false) {
  return apiJson(`/platforms/github/disconnect${purge ? "?purge=true" : ""}`, {
    method: "POST",
    errorMessage: "Unable to disconnect GitHub.",
  });
}
