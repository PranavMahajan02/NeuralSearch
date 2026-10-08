import { act, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { ApiError, apiJson, errorMessage, filenameFromDisposition } from "../api/client";
import { ErrorBoundary } from "../components/common/ErrorBoundary";
import {
  formatBytes,
  formatDuration,
  formatRelative,
  highlightParts,
  parseDate,
  relevance,
} from "../lib/format";
import { readOAuthReturn } from "../hooks/useOAuthReturn";
import { renderApp } from "./render";
import { api, server } from "./server";

describe("format helpers", () => {
  it("formats sizes and never invents one", () => {
    expect(formatBytes(null)).toBe("—");
    expect(formatBytes(500)).toBe("500 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
    expect(formatBytes(30 * 1024 ** 3)).toBe("30 GB");
  });

  it("treats zone-less backend datetimes as UTC", () => {
    expect(parseDate("2026-10-07T08:00:00")?.toISOString()).toBe("2026-10-07T08:00:00.000Z");
    expect(parseDate("2026-10-07T08:00:00Z")?.toISOString()).toBe("2026-10-07T08:00:00.000Z");
    expect(parseDate("garbage")).toBeNull();
    expect(parseDate(null)).toBeNull();
  });

  it("relative times and durations", () => {
    const now = new Date("2026-10-07T12:00:00Z");
    expect(formatRelative("2026-10-07T11:59:50Z", now)).toBe("just now");
    expect(formatRelative("2026-10-07T11:30:00Z", now)).toBe("30 min ago");
    expect(formatRelative("2026-10-07T09:00:00Z", now)).toBe("3 h ago");
    expect(formatRelative("2026-10-05T12:00:00Z", now)).toBe("2 d ago");
    expect(formatRelative(null, now)).toBe("—");
    expect(formatDuration("2026-10-07T08:00:00", "2026-10-07T08:00:42")).toBe("42s");
    expect(formatDuration("2026-10-07T08:00:00", "2026-10-07T08:03:05")).toBe("3m 5s");
    expect(formatDuration("2026-10-07T08:00:00", "2026-10-07T10:30:00")).toBe("2h 30m");
    expect(formatDuration(null, null)).toBe("—");
  });

  it("maps scores to match levels with the exact percentage", () => {
    expect(relevance(0.93)).toEqual({ level: "Strong", percent: 93 });
    expect(relevance(0.31)).toEqual({ level: "Good", percent: 31 });
    expect(relevance(0.12)).toEqual({ level: "Partial", percent: 12 });
    expect(relevance(1.4).percent).toBe(100);
  });

  it("splits highlights safely (no HTML, bad and overlapping ranges ignored)", () => {
    expect(highlightParts("<b>java</b> notes", [[3, 7]])).toEqual([
      { text: "<b>", mark: false },
      { text: "java", mark: true },
      { text: "</b> notes", mark: false },
    ]);
    expect(
      highlightParts("abc", [
        [2, 99],
        [1, 2],
        [-1, 1],
        [5, 6],
      ]),
    ).toEqual([
      { text: "a", mark: false },
      { text: "b", mark: true },
      { text: "c", mark: true },
    ]);
  });
});

describe("API client", () => {
  it("turns FastAPI errors into readable messages", () => {
    expect(errorMessage({ detail: "Nope." }, 400)).toBe("Nope.");
    expect(errorMessage({ detail: [{ msg: "a" }, { msg: "Value error, b" }] }, 422)).toBe("a; b");
    expect(errorMessage(undefined, 502)).toBe("The server ran into an error. Please try again.");
    expect(errorMessage(null, 404)).toBe("Request failed (404).");
  });

  it("handles a non-JSON error page and a network failure", async () => {
    server.use(
      http.get(api("/dashboard/recent"), () => new HttpResponse("<h1>Bad gateway</h1>", { status: 502 })),
    );
    await expect(apiJson("/dashboard/recent")).rejects.toMatchObject({ status: 502 });

    server.use(http.get(api("/dashboard/recent"), () => HttpResponse.error()));
    const error = await apiJson("/dashboard/recent").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).isNetworkError).toBe(true);
  });

  it("reads download file names", () => {
    expect(filenameFromDisposition("attachment; filename*=UTF-8''a%20b.pdf")).toBe("a b.pdf");
    expect(filenameFromDisposition('attachment; filename="c.txt"')).toBe("c.txt");
    expect(filenameFromDisposition(null)).toBeNull();
  });

  it("reads OAuth return parameters", () => {
    expect(readOAuthReturn("?x=1")).toBeNull();
    expect(readOAuthReturn("?google_drive=error&reason=weird")).toEqual({
      ok: false,
      message: "Google Drive: the connection failed.",
    });
  });
});

describe("search box", () => {
  it("autocompletes file names with the keyboard and '/' focuses it", async () => {
    server.use(
      http.get(api("/search/suggestions"), ({ request }) =>
        HttpResponse.json({
          prefix: new URL(request.url).searchParams.get("prefix"),
          suggestions: [
            { file: "java notes.pdf", platform: "local", type: "document" },
            { file: "javascript.md", platform: "github", type: "document" },
          ],
        }),
      ),
    );
    const { user } = renderApp({ route: "/search" });
    const box = await screen.findByRole("combobox", { name: "Search your files" });

    await user.click(document.body);
    await user.keyboard("/");
    expect(box).toHaveFocus();

    await user.type(box, "jav");
    expect(await screen.findByRole("option", { name: /javascript\.md/ })).toBeInTheDocument();

    await user.keyboard("{ArrowDown}{ArrowDown}");
    expect(screen.getByRole("option", { name: /javascript\.md/ })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{ArrowUp}");
    expect(screen.getByRole("option", { name: /java notes\.pdf/ })).toHaveAttribute("aria-selected", "true");

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();

    await user.keyboard("{ArrowDown}{Enter}");
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("q=java+notes.pdf"));
  });
});

describe("resilience", () => {
  function Boom(): never {
    throw new Error("render failure");
  }

  it("the error boundary shows a friendly fallback", () => {
    // React logs the caught error; keep the test output clean.
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    spy.mockRestore();

    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong");
    expect(screen.getByRole("link", { name: "Go to search" })).toBeInTheDocument();
  });

  it("shows a banner when the backend is down or the browser is offline", async () => {
    server.use(http.get(api("/search/health"), () => HttpResponse.error()));
    renderApp({ route: "/search" });

    expect(await screen.findByText("The CogniSeek server is not reachable. Retrying…")).toBeInTheDocument();

    act(() => {
      Object.defineProperty(navigator, "onLine", { configurable: true, value: false });
      window.dispatchEvent(new Event("offline"));
    });
    expect(await screen.findByText(/You are offline/)).toBeInTheDocument();

    // Back online (TanStack Query pauses queries while offline; restore its global state).
    act(() => {
      Object.defineProperty(navigator, "onLine", { configurable: true, value: true });
      window.dispatchEvent(new Event("online"));
    });
  });

  it("toggles the theme", async () => {
    const { user } = renderApp({ route: "/search" });

    await user.click(await screen.findByRole("button", { name: "Switch to dark theme" }));
    expect(document.documentElement).toHaveClass("dark");
    await user.click(screen.getByRole("button", { name: "Switch to light theme" }));
    expect(document.documentElement).not.toHaveClass("dark");
  });

  it("opens the mobile menu drawer and closes it with Escape", async () => {
    const { user } = renderApp({ route: "/search" });

    await user.click(await screen.findByRole("button", { name: "Open menu" }));
    expect(screen.getByRole("dialog", { name: "Menu" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
