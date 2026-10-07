import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { renderApp } from "./render";
import { api, makeResult, makeStats, searchResponse, server } from "./server";

describe("open a result", () => {
  it("opens cloud files in a new tab with noopener", async () => {
    server.use(
      http.post(api("/search/"), () =>
        HttpResponse.json(
          searchResponse([
            makeResult({ platform: "google_drive", source_id: "drive-id", file: "plan.docx" }),
          ]),
        ),
      ),
      http.post(api("/open/"), () =>
        HttpResponse.json({ type: "url", url: "https://drive.google.com/file/d/drive-id/view" }),
      ),
    );
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    const { user } = renderApp({ route: "/search?q=plan" });

    await user.click(await screen.findByRole("button", { name: "Open plan.docx" }));

    await waitFor(() =>
      expect(open).toHaveBeenCalledWith(
        "https://drive.google.com/file/d/drive-id/view",
        "_blank",
        "noopener,noreferrer",
      ),
    );
  });

  it("downloads local files with the token as a blob under the real file name", async () => {
    let auth: string | null = null;
    server.use(
      http.post(api("/open/"), () =>
        HttpResponse.json({
          type: "download",
          url: "/files/local?path=C%3A%5Cdocs%5Cjava+notes.pdf",
          filename: "java notes.pdf",
        }),
      ),
      http.get(api("/files/local"), ({ request }) => {
        auth = request.headers.get("Authorization");
        return new HttpResponse("PDF", {
          headers: { "Content-Disposition": "attachment; filename*=UTF-8''java%20notes.pdf" },
        });
      }),
    );
    const createUrl = vi.fn(() => "blob:fake");
    URL.createObjectURL = createUrl;
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const { user } = renderApp({ route: "/search?q=java" });

    await user.click(await screen.findByRole("button", { name: "Download java notes.pdf" }));

    expect(await screen.findByText("Downloading java notes.pdf")).toBeInTheDocument();
    expect(auth).toBe("Bearer test-token");
    expect(createUrl).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
  });

  it("shows open errors in a toast", async () => {
    server.use(
      http.post(api("/open/"), () => HttpResponse.json({ detail: "File not found." }, { status: 404 })),
    );
    const { user } = renderApp({ route: "/search?q=java" });

    await user.click(await screen.findByRole("button", { name: "Download java notes.pdf" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("File not found.");
  });

  it("opens the details modal, traps focus and closes on Escape", async () => {
    const { user } = renderApp({ route: "/search?q=java" });

    const title = await screen.findByRole("button", { name: "java notes.pdf" });
    await user.click(title);

    const dialog = screen.getByRole("dialog", { name: "java notes.pdf" });
    expect(within(dialog).getByText("2.0 KB")).toBeInTheDocument();
    expect(within(dialog).getByText("82%")).toBeInTheDocument();
    expect(dialog.contains(document.activeElement)).toBe(true);

    for (let i = 0; i < 5; i += 1) await user.tab();
    expect(dialog.contains(document.activeElement)).toBe(true);

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(document.activeElement).toBe(title);
  });
});

describe("OAuth return", () => {
  it("shows success and goes to Platforms", async () => {
    renderApp({ route: "/?github=connected" });

    expect(await screen.findByText("GitHub connected.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/platforms"));
  });

  it("explains a missing Drive permission", async () => {
    renderApp({ route: "/?google_drive=error&reason=drive_scope_not_granted" });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Google Drive: Please allow 'See and download your Google Drive files' on Google's consent screen.",
    );
  });

  it("sends a first-time user to the welcome page", async () => {
    server.use(
      http.get(api("/auth/login-state"), () => HttpResponse.json({ has_indexed: false, platforms: [] })),
    );
    renderApp({ route: "/" });

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/welcome"));
    expect(await screen.findByRole("heading", { name: /Welcome/ })).toBeInTheDocument();
  });
});

describe("connection count", () => {
  it("is the same number everywhere, from /dashboard/stats", async () => {
    server.use(
      http.get(api("/dashboard/stats"), () => HttpResponse.json(makeStats({ connected_platforms: 2 }))),
    );
    const { user } = renderApp({ route: "/search" });

    expect(await screen.findByText("2 / 3")).toBeInTheDocument();
    expect(screen.getAllByTestId("connection-count")[0]).toHaveTextContent("Platforms connected: 2 / 3");

    await user.click(screen.getByRole("link", { name: "Platforms" }));
    expect(await screen.findByText(/2 of 3 platforms connected/)).toBeInTheDocument();
    expect(screen.getAllByTestId("connection-count")[0]).toHaveTextContent("Platforms connected: 2 / 3");
  });
});
