import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { renderApp } from "./render";
import { USER, api, makeResult, makeStats, searchResponse, server } from "./server";

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

    const title = await screen.findByRole("button", { name: "View details of java notes.pdf" });
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

  it("sends a user who has not finished onboarding to step 1", async () => {
    server.use(
      http.get(api("/auth/profile"), () => HttpResponse.json({ ...USER, onboarding_completed: false })),
    );
    renderApp({ route: "/" });

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/onboarding"));
    expect(await screen.findByRole("heading", { name: "Connect Your Platforms" })).toBeInTheDocument();
  });

  it("resumes onboarding at step 1 after the OAuth return, with the toast", async () => {
    server.use(
      http.get(api("/auth/profile"), () => HttpResponse.json({ ...USER, onboarding_completed: false })),
    );
    renderApp({ route: "/?google_drive=connected" });

    expect(await screen.findByText("Google Drive connected.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent(/^\/onboarding$/));
    expect(await screen.findByText(/Step 1 of 2/)).toBeInTheDocument();
  });
});

describe("connection count", () => {
  it("is the same number everywhere and always out of 3", async () => {
    server.use(
      http.get(api("/dashboard/stats"), () => HttpResponse.json(makeStats({ connected_platforms: 2 }))),
    );
    const { user } = renderApp({ route: "/search" });

    expect(await screen.findByText("2 / 3")).toBeInTheDocument(); // insights card
    expect(screen.getByTestId("connection-count")).toHaveTextContent("2 / 3 Connected"); // header pill

    await user.click(screen.getAllByRole("link", { name: "Platforms" })[0]);
    expect(await screen.findByText(/2 of 3 platforms connected/)).toBeInTheDocument();
    expect(screen.getByTestId("connection-count")).toHaveTextContent("2 / 3 Connected");

    await user.click(screen.getAllByRole("link", { name: "Indexing Center" })[0]);
    expect(await screen.findByText("Connected Portals")).toBeInTheDocument();
    expect(screen.getByText("Connected Portals").nextSibling).toHaveTextContent("2 / 3");
    expect(document.body).not.toHaveTextContent("/ 4");
  });

  it("has only Dashboard, Platforms and Indexing Center in the navigation", async () => {
    renderApp({ route: "/search" });

    const nav = await screen.findByRole("navigation", { name: "Main" });
    const labels = Array.from(nav.querySelectorAll("a")).map((a) =>
      a.textContent?.replace(/\d+ active/, "").trim(),
    );
    expect(labels).toEqual(["Dashboard", "Platforms", "Indexing Center"]);
    expect(document.body).not.toHaveTextContent(
      /Documents Only|Images Only|Audio Only|Video Only|Google Photos/,
    );
  });
});
