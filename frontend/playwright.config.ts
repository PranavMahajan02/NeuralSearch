import { defineConfig, devices } from "@playwright/test";

// Smoke test against the REAL backend (see README "End-to-end smoke test").
//   E2E_BASE_URL  the frontend (default: start `npm run dev` on 127.0.0.1:3000)
//   E2E_API_URL   the backend (default http://127.0.0.1:8000)
const baseURL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 180_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    acceptDownloads: true,
    // No CSS transitions: accessibility scans must not sample colours mid-transition.
    contextOptions: { reducedMotion: "reduce" },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : { command: "npm run dev", url: baseURL, reuseExistingServer: true, timeout: 60_000 },
});
