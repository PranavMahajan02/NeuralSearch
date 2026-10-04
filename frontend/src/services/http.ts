import API_BASE_URL from "./api";

// Single HTTP layer for every backend call:
// - adds the Bearer token
// - parses JSON safely (a non-JSON body becomes a generic error)
// - surfaces the backend's {"detail", "code"} error message
// - on 401 for an authenticated call: clears the token and returns to login

export const TOKEN_KEY = "access_token";

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  /** Sent as JSON. */
  json?: unknown;
  /** Sent as multipart/form-data. */
  formData?: FormData;
  /** Attach the Bearer token and treat 401 as "session expired" (default true). */
  auth?: boolean;
  /** Fallback message when the backend gives none. */
  errorMessage?: string;
  signal?: AbortSignal;
}

function handleUnauthorized(): void {
  clearToken();
  // The app shows the login page whenever there is no token.
  if (window.location.pathname !== "/" || window.location.search) {
    window.location.assign("/");
  } else {
    window.location.reload();
  }
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return undefined; // not JSON
  }
}

function errorFromBody(body: unknown, status: number, fallback: string): ApiError {
  if (body && typeof body === "object") {
    const { detail, code } = body as { detail?: unknown; code?: string };

    if (typeof detail === "string" && detail) {
      return new ApiError(detail, status, code);
    }

    if (Array.isArray(detail)) {
      const message = detail
        .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : String(item)))
        .join("; ");
      return new ApiError(message || fallback, status, code);
    }
  }

  return new ApiError(fallback, status);
}

export async function apiFetch(path: string, options: RequestOptions = {}): Promise<Response> {
  const { method = "GET", json, formData, auth = true, signal } = options;

  const headers: Record<string, string> = {};

  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const token = auth ? getToken() : null;

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: formData ?? (json !== undefined ? JSON.stringify(json) : undefined),
      signal,
    });
  } catch (error) {
    if ((error as Error)?.name === "AbortError") {
      throw error;
    }
    throw new ApiError("Cannot reach the server. Check that the backend is running.", 0);
  }

  if (response.status === 401 && auth) {
    handleUnauthorized();
    throw new ApiError("Your session has expired. Please log in again.", 401, "unauthorized");
  }

  return response;
}

export async function apiJson<T = any>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await apiFetch(path, options);
  const body = await readBody(response);
  const fallback = options.errorMessage ?? `Request failed (${response.status}).`;

  if (!response.ok) {
    throw errorFromBody(body, response.status, fallback);
  }

  if (body === undefined) {
    throw new ApiError("The server returned an unexpected response.", response.status);
  }

  return body as T;
}

export async function apiBlob(
  path: string,
  options: RequestOptions = {}
): Promise<{ blob: Blob; filename: string | null }> {
  const response = await apiFetch(path, options);

  if (!response.ok) {
    const body = await readBody(response);
    throw errorFromBody(body, response.status, options.errorMessage ?? "Download failed.");
  }

  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(response.headers.get("Content-Disposition")),
  };
}

function filenameFromDisposition(header: string | null): string | null {
  if (!header) {
    return null;
  }

  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1]);
    } catch {
      /* fall through */
    }
  }

  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1] : null;
}
