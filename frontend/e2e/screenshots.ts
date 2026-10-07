// Captures the README screenshots (docs/screenshots) from a running app.
//   SHOT_BASE_URL (default http://127.0.0.1:3000), SHOT_EMAIL, SHOT_PASSWORD (a demo account
//   whose index holds only non-personal sample files).
//   Run: npx tsx e2e/screenshots.ts   (or: node --experimental-strip-types e2e/screenshots.ts)
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium, type Page } from "@playwright/test";

const BASE = process.env.SHOT_BASE_URL || "http://127.0.0.1:3000";
const OUT = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "docs", "screenshots");

async function shot(page: Page, name: string, path: string, wait: () => Promise<unknown>) {
  await page.goto(`${BASE}${path}`);
  await wait();
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: join(OUT, `${name}.png`), fullPage: false });
}

async function main() {
  const email = process.env.SHOT_EMAIL;
  const password = process.env.SHOT_PASSWORD;
  if (!email || !password) throw new Error("Set SHOT_EMAIL and SHOT_PASSWORD (a demo account).");

  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    colorScheme: "light",
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  await page.addInitScript(() => localStorage.setItem("cogniseek_theme", "light"));

  await page.goto(`${BASE}/login`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL(/\/(search|welcome)/);

  const result = () => page.locator("article").first().waitFor();
  await shot(page, "dashboard", "/search", () => page.getByText("Recently indexed").waitFor());
  await shot(page, "search-document", "/search?q=gradient%20descent%20learning%20rate", result);
  await shot(page, "search-visual-dog", "/search?q=dog", result);
  await shot(page, "search-empty", "/search?q=submarine%20volcano%20eruption", () =>
    page.getByText(/No results for/).waitFor(),
  );
  await shot(page, "platforms", "/platforms", () =>
    page
      .getByText("Registered folders")
      .or(page.getByRole("list", { name: "Registered folders" }))
      .first()
      .waitFor(),
  );
  await shot(page, "indexing", "/indexing", () =>
    page.getByRole("heading", { name: "Local storage" }).waitFor(),
  );

  await page.setViewportSize({ width: 375, height: 812 });
  await shot(page, "mobile-search", "/search?q=dog", result);

  await browser.close();
}

void main();
