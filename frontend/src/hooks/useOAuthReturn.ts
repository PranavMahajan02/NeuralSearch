// The backend's OAuth callbacks return to "/?github=connected" or
// "/?google_drive=error&reason=...". Turn that into a message once.

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

export interface OAuthResult {
  ok: boolean;
  message: string;
}

export function readOAuthReturn(search: string): OAuthResult | null {
  const params = new URLSearchParams(search);
  const key = Object.keys(LABELS).find((name) => params.has(name));

  if (!key) return null;

  if (params.get(key) === "connected") return { ok: true, message: `${LABELS[key]} connected.` };

  const reason = params.get("reason") ?? "";

  return { ok: false, message: `${LABELS[key]}: ${REASONS[reason] ?? "the connection failed."}` };
}
