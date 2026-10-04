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
  return apiJson<{ connected: boolean }>("/platforms/github/status", {
    errorMessage: "Unable to fetch GitHub status.",
  });
}

export async function disconnectGithub() {
  return apiJson("/platforms/github/disconnect", {
    method: "POST",
    errorMessage: "Unable to disconnect GitHub.",
  });
}

const GITHUB_ERRORS: Record<string, string> = {
  missing_state: "The GitHub sign-in link was incomplete. Please try again.",
  invalid_state: "The GitHub sign-in link was not recognised. Please try again.",
  state_expired: "The GitHub sign-in link expired. Please try again.",
  state_already_used: "That GitHub sign-in link was already used.",
  access_denied: "GitHub access was not granted.",
  token_exchange_failed: "GitHub could not complete the sign-in. Please try again.",
};

/**
 * Reads ?github=connected|error&reason=... left by the OAuth callback,
 * removes it from the address bar, and returns a message to show (or null).
 */
export function consumeGithubRedirectResult(): { ok: boolean; message: string } | null {
  const params = new URLSearchParams(window.location.search);
  const result = params.get("github");

  if (!result) {
    return null;
  }

  const reason = params.get("reason") || "";

  params.delete("github");
  params.delete("reason");
  const query = params.toString();
  window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""));

  if (result === "connected") {
    return { ok: true, message: "GitHub connected successfully." };
  }

  return { ok: false, message: GITHUB_ERRORS[reason] || "GitHub connection failed." };
}
