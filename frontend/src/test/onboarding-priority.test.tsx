import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { JobWithHistory, SearchRequest } from "../api/types";
import { allIndexed, platformState, priorityProgress, queuePosition } from "../lib/indexing";
import { renderApp } from "./render";
import { USER, api, makeJob, makeStats, searchResponse, server } from "./server";

function newUser() {
  server.use(
    http.get(api("/auth/profile"), () => HttpResponse.json({ ...USER, onboarding_completed: false })),
  );
}

function connectedFolder() {
  server.use(
    http.get(api("/platforms/local/folders"), () =>
      HttpResponse.json({ folders: ["C:\\docs"], picker_available: false }),
    ),
    http.get(api("/platforms/google-drive/status"), () =>
      HttpResponse.json({ connected: true, account_email: "me@example.com" }),
    ),
    http.get(api("/platforms/github/status"), () =>
      HttpResponse.json({ connected: false, account_name: null }),
    ),
  );
}

describe("onboarding", () => {
  it("can be skipped at step 1", async () => {
    newUser();
    let skipped = false;
    server.use(
      http.post(api("/auth/onboarding/skip"), () => {
        skipped = true;
        return HttpResponse.json({ onboarding_completed: true });
      }),
    );
    const { user } = renderApp({ route: "/onboarding" });

    await user.click(await screen.findByRole("button", { name: /Skip for now/ }));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/search"));
    expect(skipped).toBe(true);
  });

  it("step 1 needs a connection; step 2 can also be skipped", async () => {
    newUser();
    server.use(
      http.get(api("/platforms/local/folders"), () =>
        HttpResponse.json({ folders: [], picker_available: false }),
      ),
      http.get(api("/platforms/google-drive/status"), () =>
        HttpResponse.json({ connected: false, account_email: null }),
      ),
      http.post(api("/auth/onboarding/skip"), () => HttpResponse.json({ onboarding_completed: true })),
    );
    const { user } = renderApp({ route: "/onboarding" });

    const next = await screen.findByRole("button", { name: /Continue to Priority Indexing/ });
    expect(next).toBeDisabled();
    expect(screen.getByText("Connect at least one platform to continue.")).toBeInTheDocument();

    connectedFolder();
    renderApp({ route: "/onboarding?step=2" });
    const steps = await screen.findAllByText(/Step 2 of 2/);
    expect(steps.length).toBeGreaterThan(0);
    await user.click(screen.getAllByRole("button", { name: /Skip for now/ }).at(-1)!);
    await waitFor(() => expect(screen.getAllByTestId("location").at(-1)).toHaveTextContent("/search"));
  });

  it("starts indexing with the chosen priority and every connected platform, then completes", async () => {
    newUser();
    connectedFolder();
    let body: unknown;
    let completed = false;
    server.use(
      http.post(api("/index/"), async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({
          status: "success",
          message: "Indexing queued",
          priority_platform: "google_drive",
          platforms: [],
          jobs: [],
        });
      }),
      http.post(api("/auth/onboarding/complete"), () => {
        completed = true;
        return HttpResponse.json({ onboarding_completed: true });
      }),
    );
    const { user } = renderApp({ route: "/onboarding" });

    // Step 1 shows both connections; continue.
    expect(await screen.findByText("me@example.com")).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: /Continue to Priority Indexing/ }));

    // Step 2: pick Google Drive as the priority.
    expect(await screen.findByRole("heading", { name: "Choose your priority platform" })).toBeInTheDocument();
    expect(screen.getByText(/the others index in the background/)).toBeInTheDocument();
    const start = screen.getByRole("button", { name: /Start indexing/ });
    expect(start).toBeDisabled();
    await user.click(screen.getByRole("radio", { name: /Google Drive/ }));
    expect(screen.getByText("1. Index Google Drive")).toBeInTheDocument();
    await user.click(start);

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/search"));
    expect(body).toEqual({ priority_platform: "google_drive", platforms: ["local", "google_drive"] });
    expect(completed).toBe(true);
  });

  it("is never shown again to a user who finished it", async () => {
    renderApp({ route: "/onboarding" });
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/search"));
  });
});

const T0 = "2026-10-07T08:00:00";
const at = (seconds: number) =>
  new Date(Date.parse(`${T0}Z`) + seconds * 1000).toISOString().replace("Z", "");

function batch(priorityStatus: JobWithHistory["status"]) {
  return [
    makeJob({
      id: "p",
      platform: "local",
      status: priorityStatus,
      total_files: 340,
      processed_files: 120,
      progress: 35,
      created_at: at(0),
    }),
    makeJob({
      id: "d",
      platform: "google_drive",
      status: "queued",
      total_files: 0,
      processed_files: 0,
      created_at: at(0.001),
    }),
    makeJob({
      id: "g",
      platform: "github",
      status: "queued",
      total_files: 0,
      processed_files: 0,
      created_at: at(0.002),
    }),
  ];
}

describe("priority banner and platform default", () => {
  it("while the priority platform indexes: progress text, background list, filter defaults to it", async () => {
    const searches: SearchRequest[] = [];
    server.use(
      http.get(api("/index/jobs"), () => HttpResponse.json(batch("running"))),
      http.post(api("/search/"), async ({ request }) => {
        searches.push((await request.json()) as SearchRequest);
        return HttpResponse.json(searchResponse([]));
      }),
    );
    renderApp({ route: "/search?q=notes" });

    const banner = await screen.findByText(/Local Storage indexing 120\/340 — results may be incomplete/);
    expect(banner.closest("[role=status]")).toHaveTextContent("Google Drive, GitHub indexing in background");
    expect(screen.getByRole("link", { name: "Indexing Center" })).toBeInTheDocument();
    await waitFor(() => expect(searches.at(-1)?.platform).toBe("local"));
    expect(screen.getByLabelText("Platform")).toHaveValue("local");
  });

  it("once the priority platform is done: ready, and the filter is All again", async () => {
    const searches: SearchRequest[] = [];
    server.use(
      http.get(api("/index/jobs"), () => HttpResponse.json(batch("completed"))),
      http.post(api("/search/"), async ({ request }) => {
        searches.push((await request.json()) as SearchRequest);
        return HttpResponse.json(searchResponse([]));
      }),
    );
    renderApp({ route: "/search?q=notes" });

    expect(await screen.findByText(/Searching Local Storage ✓ ready/)).toBeInTheDocument();
    await waitFor(() => expect(searches.at(-1)?.platform).toBe("all"));
  });

  it("disappears when nothing is queued or running", async () => {
    renderApp({ route: "/search" });
    await screen.findByText("System Indexing Insights");
    expect(screen.queryByText(/indexing in background|✓ ready/)).not.toBeInTheDocument();
  });
});

describe("Indexing Center queue", () => {
  it('shows queue positions and moves a job with "Index next"', async () => {
    let prioritized = "";
    server.use(
      http.get(api("/index/jobs"), () => HttpResponse.json(batch("running"))),
      http.get(api("/dashboard/stats"), () => HttpResponse.json(makeStats())),
      http.post(api("/index/jobs/:id/prioritize"), ({ params }) => {
        prioritized = String(params.id);
        return HttpResponse.json(makeJob({ id: "g", platform: "github", status: "queued", priority: 1 }));
      }),
    );
    const { user } = renderApp({ route: "/indexing" });

    const drive = (await screen.findByRole("heading", { name: "Google Drive", level: 3 })).closest(
      "section",
    )!;
    const github = screen.getByRole("heading", { name: "GitHub", level: 3 }).closest("section")!;
    expect(within(drive).getByText("Queued (#1)")).toBeInTheDocument();
    expect(within(drive).queryByRole("button", { name: "Index next" })).not.toBeInTheDocument();
    expect(within(github).getByText("Queued (#2)")).toBeInTheDocument();

    await user.click(within(github).getByRole("button", { name: "Index next" }));
    expect(await screen.findByText("GitHub will be indexed next.")).toBeInTheDocument();
    expect(prioritized).toBe("g");

    // Roadmap shows the real state per platform.
    const roadmap = screen.getByRole("heading", { name: "Platform Sync Roadmap" }).closest("section")!;
    expect(roadmap).toHaveTextContent("Indexing 35%");
    expect(roadmap).toHaveTextContent("Queued");
  });

  it('shows "All platforms indexed" only when every connected platform is ready', async () => {
    server.use(
      http.get(api("/index/jobs"), () =>
        HttpResponse.json([
          makeJob({ id: "a", platform: "local", status: "completed" }),
          makeJob({ id: "b", platform: "google_drive", status: "completed" }),
        ]),
      ),
    );
    renderApp({ route: "/indexing" });

    expect(await screen.findByText(/All platforms indexed/)).toBeInTheDocument();
  });
});

describe("indexing helpers", () => {
  it("orders the queue by priority, then age", () => {
    const jobs = [
      makeJob({ id: "a", status: "queued", created_at: at(0) }),
      makeJob({ id: "b", status: "queued", created_at: at(1) }),
      makeJob({ id: "c", status: "queued", created_at: at(2), priority: 1 }),
    ];
    expect(jobs.map((j) => queuePosition(jobs, j))).toEqual([2, 3, 1]);
    expect(queuePosition(jobs, makeJob({ status: "running" }))).toBeNull();
  });

  it("finds the priority job of the current batch", () => {
    expect(priorityProgress([makeJob({ status: "completed" })])).toBeNull();
    const old = makeJob({
      id: "old",
      platform: "github",
      status: "completed",
      created_at: "2026-01-01T00:00:00",
    });
    const progress = priorityProgress([old, ...batch("completed")])!;
    expect(progress.priority.id).toBe("p");
    expect(progress.priorityDone).toBe(true);
    expect(progress.others.map((j) => j.id)).toEqual(["d", "g"]);
  });

  it("maps platform states", () => {
    expect(platformState(false, undefined)).toBe("not_connected");
    expect(platformState(true, undefined)).toBe("not_indexed");
    expect(platformState(true, makeJob({ status: "failed" }))).toBe("failed");
    expect(platformState(true, makeJob({ status: "cancelled", indexed: false }))).toBe("cancelled");
    expect(platformState(true, makeJob({ status: "cancelled", indexed: true }))).toBe("ready");
    expect(allIndexed(["ready", "not_connected"])).toBe(true);
    expect(allIndexed(["ready", "failed"])).toBe(false);
    expect(allIndexed(["not_connected"])).toBe(false);
  });
});

describe("live counts", () => {
  it("refreshes the insight numbers while a job runs, and stops when idle", async () => {
    let statsCalls = 0;
    let status: "running" | "completed" = "running";
    server.use(
      http.get(api("/index/jobs"), () => HttpResponse.json(batch(status))),
      http.get(api("/dashboard/stats"), () => {
        statsCalls += 1;
        return HttpResponse.json(makeStats({ total_files: statsCalls }));
      }),
    );
    renderApp({ route: "/search" });

    await screen.findByText("System Indexing Insights");
    await waitFor(() => expect(statsCalls).toBeGreaterThanOrEqual(2), { timeout: 4000 });

    status = "completed";
    await waitFor(() => expect(screen.queryByText(/results may be incomplete/)).not.toBeInTheDocument(), {
      timeout: 4000,
    });
  }, 15_000);
});
