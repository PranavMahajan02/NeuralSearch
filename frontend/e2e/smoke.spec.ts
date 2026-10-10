// End-to-end smoke test against the real backend:
// throwaway user -> register a temp folder with 3 files -> index -> search ->
// download -> accessibility checks -> delete the account in the UI (the real
// DELETE /auth/account flow) -> clean up the temp folder.
import { randomBytes } from "node:crypto";
import { chmodSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative } from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const API = process.env.E2E_API_URL || "http://127.0.0.1:8000";
const id = randomBytes(4).toString("hex");
const email = `e2e-${id}@cogniseek.dev`;
const password = `E2e-${randomBytes(9).toString("base64url")}7`;
const marker = `zephyrquartz${id}`; // a word that exists only in this test's files

let folder = "";

/** The path the backend sees. In Docker the host folder E2E_FILES_ROOT is mounted
 * at E2E_CONTAINER_ROOT (e.g. ./sample-data -> /data), so the path is mapped. */
function backendPath(hostPath: string): string {
  const containerRoot = process.env.E2E_CONTAINER_ROOT;
  if (!containerRoot || !process.env.E2E_FILES_ROOT) return hostPath;
  const rel = relative(process.env.E2E_FILES_ROOT, hostPath).split(/[\\/]/).join("/");
  return `${containerRoot.replace(/\/+$/, "")}/${rel}`;
}

test.beforeAll(async ({ request }) => {
  // The folder must be inside the backend's ALLOWED_LOCAL_ROOTS (default: the home directory).
  folder = mkdtempSync(join(process.env.E2E_FILES_ROOT || tmpdir(), "cogniseek-e2e-"));
  writeFileSync(
    join(folder, "e2e-field-notes.txt"),
    `Field notes. The ${marker} sample was found near the river.\n`,
  );
  writeFileSync(
    join(folder, "e2e-recipe.md"),
    "# Lemon cake\n\nMix flour, sugar, eggs and lemon zest. Bake 35 minutes.\n",
  );
  writeFileSync(join(folder, "e2e-inventory.csv"), "item,count\nbolts,40\nwashers,120\n");
  // mkdtemp creates the folder as 0700; a backend in a container runs as another
  // user (uid 10001) and must be able to read it.
  chmodSync(folder, 0o755);
  for (const name of readdirSync(folder)) chmodSync(join(folder, name), 0o644);

  const response = await request.post(`${API}/auth/register`, {
    data: { name: "E2E Smoke", email, password },
  });
  expect(response.ok(), await response.text()).toBe(true);
});

test.afterAll(async ({ request }) => {
  // Normally the test already deleted the account in the UI; if it failed earlier,
  // delete it through the same API (a 401 at login means it is already gone).
  const login = await request.post(`${API}/auth/login`, { data: { email, password } });
  if (login.ok()) {
    const { access_token } = (await login.json()) as { access_token: string };
    const deleted = await request.delete(`${API}/auth/account`, {
      headers: { Authorization: `Bearer ${access_token}` },
      data: { password },
    });
    expect(deleted.ok(), await deleted.text()).toBe(true);
  }
  if (folder) rmSync(folder, { recursive: true, force: true });
});

async function expectNoSeriousA11yViolations(page: Page) {
  await page.waitForLoadState("networkidle");
  // Let entrance fades finish: axe must not sample colours mid-animation (infinite loops are ignored).
  await page.waitForFunction(() =>
    document
      .getAnimations()
      .every((a) => a.playState !== "running" || a.effect?.getTiming().iterations === Infinity),
  );
  await page.waitForTimeout(600); // JS-driven (motion) fades are not in getAnimations()
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  const describe = (v: (typeof serious)[number]) =>
    `${v.id}: ${v.help} -> ${v.nodes.map((n) => `${n.target.join(" ")} [${n.failureSummary ?? ""}]`).join("; ")}`;

  expect(serious.map(describe)).toEqual([]);
}

test("new user: onboarding, priority = local, dashboard banner, search, download, delete account", async ({
  page,
}) => {
  // Behind Caddy the strict CSP applies: any blocked script/style/font fails the test.
  const cspViolations: string[] = [];
  page.on("console", (message) => {
    if (/Content Security Policy/i.test(message.text())) cspViolations.push(message.text());
  });

  // Log in through the UI (the original sign-in card).
  await page.goto("/login");
  await expectNoSeriousA11yViolations(page);
  await page.getByRole("button", { name: "Sign In with Email" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();

  // Onboarding step 1: a new user lands here; add the local folder.
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByRole("heading", { name: "Connect Your Platforms" })).toBeVisible();
  await expectNoSeriousA11yViolations(page);
  await page.getByLabel(/Add a folder/).fill(backendPath(folder));
  await page.getByRole("button", { name: "Add folder" }).click();
  await expect(page.getByRole("list", { name: "Registered folders" })).toContainText("cogniseek-e2e-");
  await page.getByRole("button", { name: /Continue to Priority Indexing/ }).click();

  // Step 2: local storage is the priority platform.
  await expect(page.getByRole("heading", { name: "Choose your priority platform" })).toBeVisible();
  await page.getByRole("radio", { name: /Local Storage/ }).check();
  await expectNoSeriousA11yViolations(page);
  await page.getByRole("button", { name: /Start indexing/ }).click();

  // Dashboard: search works at once; the banner shows the priority platform until nothing runs.
  await expect(page).toHaveURL(/\/search/);
  await expect(page.getByRole("heading", { name: "Search across your world" })).toBeVisible();
  await expect(page.getByText(/Local Storage indexing|Searching Local Storage ✓ ready/)).toBeVisible();

  // The Indexing Center shows the job finish.
  await page.getByRole("link", { name: "Indexing Center" }).first().click();
  const local = page.locator("section", {
    has: page.getByRole("heading", { name: "Local Storage", level: 3 }),
  });
  await expect(local.getByText("Completed", { exact: true }).first()).toBeVisible({ timeout: 150_000 });
  await expect(local.getByText("Indexed", { exact: true }).first().locator("..")).toContainText("3");
  await expectNoSeriousA11yViolations(page);

  // Search for the word only this test's file contains.
  await page.getByRole("link", { name: "Dashboard" }).first().click();
  await expect(page.getByText(/indexing in background|✓ ready/)).toHaveCount(0); // banner gone
  await page.getByRole("combobox", { name: "Search your files" }).fill(marker);
  await page.keyboard.press("Enter");
  const card = page.locator("article", { has: page.getByRole("heading", { name: "e2e-field-notes.txt" }) });
  await expect(card).toBeVisible();
  await expect(card.locator("mark").first()).toHaveText(marker);
  await expectNoSeriousA11yViolations(page);

  // Download it (local files are downloaded with the user's token).
  const download = page.waitForEvent("download");
  await card.getByRole("button", { name: "Download e2e-field-notes.txt" }).click();
  expect((await download).suggestedFilename()).toBe("e2e-field-notes.txt");

  // Dark mode passes the same accessibility checks.
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expectNoSeriousA11yViolations(page);
  await page.getByRole("link", { name: "Platforms" }).first().click();
  await expect(page.getByRole("heading", { name: "Unified Platforms Integration" })).toBeVisible();
  await expectNoSeriousA11yViolations(page);
  await page.getByRole("link", { name: "Indexing Center" }).first().click();
  await expectNoSeriousA11yViolations(page);

  // Delete the account: typed confirmation + password, then signed out for good.
  await page.getByRole("button", { name: "Account settings" }).first().click();
  const settings = page.getByRole("dialog", { name: "Account settings" });
  await expectNoSeriousA11yViolations(page);
  const danger = settings.getByRole("region", { name: "Delete account" });
  await danger.getByLabel(/Type DELETE/).fill("DELETE");
  await danger.getByLabel("Password").fill(password);
  await danger.getByRole("button", { name: "Delete my account" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText("Your account and all of its data were deleted.")).toBeVisible();

  const relogin = await page.request.post(`${API}/auth/login`, { data: { email, password } });
  expect(relogin.status()).toBe(401);
  expect(cspViolations).toEqual([]);
});
