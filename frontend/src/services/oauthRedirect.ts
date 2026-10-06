// Reads ?github=... / ?google_drive=... left by the backend OAuth callbacks,
// removes it from the address bar, and returns a message to show (or null).

const REASONS: Record<string, string> = {
  missing_state: "The sign-in link was incomplete. Please try again.",
  invalid_state: "The sign-in link was not recognised. Please try again.",
  state_expired: "The sign-in link expired. Please try again.",
  state_already_used: "That sign-in link was already used.",
  access_denied: "Access was not granted.",
  token_exchange_failed: "The sign-in could not be completed. Please try again.",
  drive_scope_not_granted:
    "Please allow 'See and download your Google Drive files' on Google's consent screen.",
};

const LABELS: Record<string, string> = { github: "GitHub", google_drive: "Google Drive" };

export function consumeOAuthRedirect(): { ok: boolean; message: string } | null {
  const params = new URLSearchParams(window.location.search);

  const key = Object.keys(LABELS).find((name) => params.has(name));
  if (!key) {
    return null;
  }

  const result = params.get(key);
  const reason = params.get("reason") || "";

  params.delete(key);
  params.delete("reason");
  const query = params.toString();
  window.history.replaceState(null, "", window.location.pathname + (query ? `?${query}` : ""));

  if (result === "connected") {
    return { ok: true, message: `${LABELS[key]} connected successfully.` };
  }

  return { ok: false, message: `${LABELS[key]}: ${REASONS[reason] || "connection failed."}` };
}
