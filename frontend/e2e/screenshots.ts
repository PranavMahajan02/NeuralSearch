// Captures the README screenshots (docs/screenshots) by walking a throwaway demo
// account through the real flow: login -> onboarding (folder, priority) ->
// dashboard with the priority banner -> results -> platforms -> indexing (light + dark).
//   SHOT_BASE_URL (frontend, default http://127.0.0.1:3000), SHOT_API_URL (backend, default :8000),
//   SHOT_FOLDER: a folder holding only non-personal sample files.
//   Run: node --experimental-strip-types e2e/screenshots.ts   (the demo user is deleted afterwards)
import { execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { existsSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium, type Page } from "@playwright/test";

const BASE = process.env.SHOT_BASE_URL || "http://127.0.0.1:3000";
const API = process.env.SHOT_API_URL || "http://127.0.0.1:8000";
const FOLDER = process.env.SHOT_FOLDER;
const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const OUT = join(REPO, "docs", "screenshots");
const PYTHON =
  [join(REPO, "venv", "Scripts", "python.exe"), join(REPO, "venv", "bin", "python")].find(existsSync) ||
  "python";

const email = `e2e-demo-${randomBytes(3).toString("hex")}@cogniseek.dev`;
const password = `Demo-${randomBytes(9).toString("base64url")}7`;

async function settle(page: Page) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(900);
}

async function shot(page: Page, name: string) {
  await settle(page);
  await page.screenshot({ path: join(OUT, `${name}.png`) });
}

async function main() {
  if (!FOLDER) throw new Error("Set SHOT_FOLDER to a folder of non-personal sample files.");
  mkdirSync(OUT, { recursive: true });

  const created = await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "Demo User", email, password }),
  });
  if (!created.ok) throw new Error(`register failed: ${created.status}`);

  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: "light" });
  const page = await context.newPage();
  await page.addInitScript(() => {
    if (!localStorage.getItem("cogniseek_theme")) localStorage.setItem("cogniseek_theme", "light");
  });

  try {
    await page.goto(`${BASE}/login`);
    await page.getByRole("button", { name: "Sign In with Email" }).click();
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await shot(page, "login");
    await page.getByRole("button", { name: "Sign In", exact: true }).click();

    await page.getByRole("heading", { name: "Connect Your Platforms" }).waitFor();
    await page.getByLabel(/Add a folder/).fill(FOLDER);
    await page.getByRole("button", { name: "Add folder" }).click();
    await page.getByRole("list", { name: "Registered folders" }).waitFor();
    await shot(page, "onboarding-step1");

    await page.getByRole("button", { name: /Continue to Priority Indexing/ }).click();
    await page.getByRole("radio", { name: /Local Storage/ }).check();
    await shot(page, "onboarding-step2");
    await page.getByRole("button", { name: /Start indexing/ }).click();

    await page.getByText(/Local Storage indexing/).waitFor({ timeout: 30_000 });
    await shot(page, "dashboard-banner");

    await page.goto(`${BASE}/indexing`);
    await page
      .getByRole("progressbar")
      .first()
      .waitFor({ timeout: 30_000 })
      .catch(() => undefined);
    await shot(page, "indexing-center-running");

    // Wait for the job to finish, then the remaining pages.
    await page.getByText("Completed", { exact: true }).first().waitFor({ timeout: 240_000 });
    await shot(page, "indexing-center");

    await page.goto(`${BASE}/search`);
    await page.getByText("System Indexing Insights").waitFor();
    await shot(page, "dashboard");
    await page.goto(`${BASE}/search?q=gradient%20descent%20learning%20rate`);
    await page.locator("article").first().waitFor();
    await shot(page, "search-document");
    await page.goto(`${BASE}/search?q=dog`);
    await page.locator("article").first().waitFor();
    await shot(page, "search-visual-dog");
    await page.goto(`${BASE}/search?q=submarine%20volcano%20eruption`);
    await page.getByText(/No results for/).waitFor();
    await shot(page, "search-empty");
    await page.goto(`${BASE}/platforms`);
    await page.getByRole("list", { name: "Registered folders" }).waitFor();
    await shot(page, "platforms");

    // Dark mode.
    await page.getByRole("button", { name: "Switch to dark theme" }).click();
    await shot(page, "platforms-dark");
    await page.goto(`${BASE}/indexing`);
    await page.getByRole("heading", { name: "Platform Sync Roadmap" }).waitFor();
    await shot(page, "indexing-center-dark");
    await page.goto(`${BASE}/search?q=dog`);
    await page.locator("article").first().waitFor();
    await shot(page, "search-visual-dog-dark");

    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${BASE}/search`);
    await shot(page, "mobile-dashboard-dark");
  } finally {
    await browser.close();
    execFileSync(PYTHON, [join(REPO, "scripts", "delete_e2e_user.py"), email], {
      cwd: REPO,
      stdio: "inherit",
    });
  }
}

void main();
