// The single HTTP layer: base URL, Bearer token, JSON parsing, error messages.
// Every error thrown here is an ApiError whose message is safe to show.

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const TOKEN_KEY = "access_token";

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }

  /** The backend could not be reached at all (network down, server stopped). */
  get isNetworkError(): boolean {
    return this.status === 0;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// Set by the AuthProvider: what to do when an authenticated call gets 401.
let unauthorizedHandler: () => void = () => undefined;

export function onUnauthorized(handler: () => void): void {
  unauthorizedHandler = handler;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  /** Sent as JSON. */
  json?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
  /** Attach the token and treat 401 as "session expired" (default true). */
  auth?: boolean;
  signal?: AbortSignal;
}

export function apiUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(path, API_BASE_URL);

  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined) url.searchParams.set(key, String(value));
  }

  return url.toString();
}

async function request(path: string, options: RequestOptions): Promise<Response> {
  const { method = "GET", json, query, auth = true, signal } = options;
  const headers: Record<string, string> = {};

  if (json !== undefined) headers["Content-Type"] = "application/json";

  const token = auth ? getToken() : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;

  try {
    response = await fetch(apiUrl(path, query), {
      method,
      headers,
      body: json !== undefined ? JSON.stringify(json) : undefined,
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("Cannot reach the server. Check that the backend is running.", 0, "network");
  }

  if (response.status === 401 && auth) {
    clearToken();
    unauthorizedHandler();
    throw new ApiError("Your session has expired. Please log in again.", 401, "unauthorized");
  }

  return response;
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return undefined; // not JSON (e.g. a proxy's HTML error page)
  }
}

/** FastAPI errors: {"detail": "..."} or a 422 {"detail": [{"msg": ...}, ...]}. */
export function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;

    if (typeof detail === "string" && detail) return detail;

    if (Array.isArray(detail) && detail.length) {
      return detail
        .map((item: unknown) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg).replace(/^Value error, /, "")
            : String(item),
        )
        .join("; ");
    }
  }

  return status >= 500 ? "The server ran into an error. Please try again." : `Request failed (${status}).`;
}

function codeOf(body: unknown): string | undefined {
  return body && typeof body === "object" && "code" in body
    ? String((body as { code: unknown }).code)
    : undefined;
}

export async function apiJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await request(path, options);
  const body = await readBody(response);

  if (!response.ok) throw new ApiError(errorMessage(body, response.status), response.status, codeOf(body));

  if (body === undefined) throw new ApiError("The server returned an unexpected response.", response.status);

  return body as T;
}

export async function apiBlob(
  path: string,
  options: RequestOptions = {},
): Promise<{ blob: Blob; filename: string | null }> {
  const response = await request(path, options);

  if (!response.ok) {
    const body = await readBody(response);
    throw new ApiError(errorMessage(body, response.status), response.status, codeOf(body));
  }

  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(response.headers.get("Content-Disposition")),
  };
}

export function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null;

  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1]);
    } catch {
      /* fall back to the plain filename */
    }
  }

  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1] : null;
}
