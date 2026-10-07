import { screen, waitFor, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { renderApp } from "./render";
import { api, makeJob, server } from "./server";

describe("indexing center", () => {
  it("shows a running job: progress, current file, counters and Cancel", async () => {
    let cancelled = "";
    server.use(
      http.get(api("/index/jobs"), () =>
        HttpResponse.json([
          makeJob({
            status: "running",
            total_files: 40,
            processed_files: 10,
            succeeded_files: 9,
            failed_files: 1,
            skipped_files: 3,
            downloaded_files: 4,
            progress: 25,
            current_file: "C:\\docs\\big.pdf",
            completed_at: null,
          }),
        ]),
      ),
      http.post(api("/index/jobs/job-1/cancel"), ({ params }) => {
        cancelled = String(params.id ?? "job-1");
        return HttpResponse.json(makeJob({ status: "running", cancel_requested: true }));
      }),
    );
    const { user } = renderApp({ route: "/indexing" });

    const card = (await screen.findByRole("heading", { name: "Local storage" })).closest("section")!;
    const scope = within(card);
    expect(scope.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "25");
    expect(scope.getByText("10 of 40 files (25%)")).toBeInTheDocument();
    expect(scope.getByText("C:\\docs\\big.pdf")).toBeInTheDocument();
    expect(scope.getByText("Downloaded").nextSibling).toHaveTextContent("4");
    expect(scope.getByText("Running")).toBeInTheDocument();

    await user.click(scope.getByRole("button", { name: "Cancel" }));
    expect(await screen.findByText(/Cancel requested/)).toBeInTheDocument();
    expect(cancelled).toBe("job-1");
  });

  it("shows a failed job's message, its file errors and the run history", async () => {
    server.use(
      http.get(api("/index/jobs"), () =>
        HttpResponse.json([
          makeJob({
            status: "failed",
            platform: "google_drive",
            error_message: "Google Drive permission missing — reconnect and allow Drive access.",
            failed_files: 2,
            history: [
              makeJob({ id: "old", status: "completed" }),
              makeJob({ id: "older", status: "cancelled" }),
            ],
          }),
        ]),
      ),
      http.get(api("/index/jobs/job-1/errors"), () =>
        HttpResponse.json({
          job_id: "job-1",
          failed_files: 2,
          errors: [
            { file: "report.pdf", error: "Could not save vectors (request too large)", created_at: null },
          ],
        }),
      ),
    );
    const { user } = renderApp({ route: "/indexing" });

    const card = (await screen.findByRole("heading", { name: "Google Drive" })).closest("section")!;
    const scope = within(card);
    expect(scope.getByRole("alert")).toHaveTextContent("permission missing");

    await user.click(scope.getByRole("button", { name: "Show 2 file errors" }));
    expect(await scope.findByText("Could not save vectors (request too large)")).toBeInTheDocument();

    expect(scope.getByText("Last 2 runs")).toBeInTheDocument();
    expect(scope.getByRole("table")).toHaveTextContent("Cancelled");
    expect(screen.getAllByText("Never indexed.")).toHaveLength(2);
  });

  it("has ONE /index/jobs poller: 2 s while active, none when idle", async () => {
    let requests = 0;
    let status: "running" | "completed" = "running";
    server.use(
      http.get(api("/index/jobs"), () => {
        requests += 1;
        return HttpResponse.json([makeJob({ status })]);
      }),
    );
    // The sidebar badge and the page both read the jobs query.
    renderApp({ route: "/indexing" });

    await screen.findByRole("progressbar");
    expect(requests).toBe(1);

    await waitFor(() => expect(requests).toBe(2), { timeout: 3000 });
    status = "completed";
    await waitFor(() => expect(requests).toBe(3), { timeout: 3000 });

    await delay(2500); // idle: polling stopped
    expect(requests).toBe(3);
  }, 15_000);
});

describe("platforms", () => {
  it("shows the backend's validation message for a bad folder", async () => {
    server.use(
      http.post(api("/platforms/local/folders"), () =>
        HttpResponse.json({ detail: "Folder is outside the allowed locations." }, { status: 400 }),
      ),
    );
    const { user } = renderApp({ route: "/platforms" });

    await user.type(await screen.findByLabelText(/Add a folder/), "C:\\Windows");
    await user.click(screen.getByRole("button", { name: "Add folder" }));

    expect(await screen.findByText("Folder is outside the allowed locations.")).toBeInTheDocument();
    expect(screen.getByLabelText(/Add a folder/)).toHaveAttribute("aria-invalid", "true");
  });

  it("only offers Browse when the backend has a folder picker", async () => {
    renderApp({ route: "/platforms" });
    await screen.findByText("C:\\docs");
    expect(screen.queryByRole("button", { name: "Browse…" })).not.toBeInTheDocument();
  });

  it("warns before removing a folder and reports the purge", async () => {
    let removed: unknown;
    server.use(
      http.delete(api("/platforms/local/folders"), async ({ request }) => {
        removed = await request.json();
        return HttpResponse.json({
          folders: [],
          picker_available: false,
          status: "success",
          purged_files: 5,
        });
      }),
    );
    const { user } = renderApp({ route: "/platforms" });

    await user.click(await screen.findByRole("button", { name: "Remove folder C:\\docs" }));
    const dialog = screen.getByRole("dialog", { name: "Remove this folder?" });
    expect(dialog).toHaveTextContent("removed from the search index");

    await user.click(within(dialog).getByRole("button", { name: "Remove and purge" }));
    expect(await screen.findByText("Folder removed; 5 indexed files purged.")).toBeInTheDocument();
    expect(removed).toEqual({ folder: "C:\\docs" });
  });

  it("disconnects with the purge option", async () => {
    let url = "";
    server.use(
      http.post(api("/platforms/google-drive/disconnect"), ({ request }) => {
        url = request.url;
        return HttpResponse.json({
          status: "success",
          connected: false,
          revoked: true,
          purged_files: 7,
          message: "ok",
        });
      }),
    );
    const { user } = renderApp({ route: "/platforms" });

    const card = (await screen.findByRole("heading", { name: "Google Drive" })).closest("section")!;
    expect(await within(card).findByText("me@example.com")).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Disconnect" }));

    const dialog = screen.getByRole("dialog");
    await user.click(within(dialog).getByRole("checkbox"));
    await user.click(within(dialog).getByRole("button", { name: "Disconnect" }));

    expect(
      await screen.findByText("Google Drive disconnected; 7 indexed files removed."),
    ).toBeInTheDocument();
    expect(new URL(url).searchParams.get("purge")).toBe("true");
  });

  it("offers Reconnect after a permission failure and redirects to the provider", async () => {
    server.use(
      http.get(api("/platforms/google-drive/status"), () =>
        HttpResponse.json({ connected: false, account_email: null }),
      ),
      http.get(api("/index/jobs"), () =>
        HttpResponse.json([
          makeJob({
            platform: "google_drive",
            status: "failed",
            error_message: "Google Drive permission missing — reconnect and allow Drive access.",
          }),
        ]),
      ),
      http.get(api("/platforms/google-drive/connect"), () =>
        HttpResponse.json({
          status: "success",
          connected: false,
          authorization_url: "https://accounts.google.com/o",
        }),
      ),
    );
    const assign = vi.fn();
    vi.stubGlobal("location", { ...window.location, assign });
    const { user } = renderApp({ route: "/platforms" });

    const card = (await screen.findByRole("heading", { name: "Google Drive" })).closest("section")!;
    expect(await within(card).findByRole("alert")).toHaveTextContent("reconnect and allow Drive access");

    await user.click(within(card).getByRole("button", { name: "Reconnect" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("https://accounts.google.com/o"));
    vi.unstubAllGlobals();
  });

  it("re-indexes a platform and reports a conflict from the backend", async () => {
    server.use(
      http.post(api("/index/"), () =>
        HttpResponse.json(
          { detail: "Indexing is already queued or running for: local.", code: "job_already_active" },
          { status: 409 },
        ),
      ),
    );
    const { user } = renderApp({ route: "/platforms" });

    await user.click(await screen.findByRole("button", { name: "Index local folders" }));
    expect(await screen.findByText("Indexing is already queued or running for: local.")).toBeInTheDocument();
  });
});
