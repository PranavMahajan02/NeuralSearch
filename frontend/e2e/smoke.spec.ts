// End-to-end smoke test against the real backend:
// throwaway user -> register a temp folder with 3 files -> index -> search ->
// download -> accessibility checks -> clean up (user, index data, temp folder).
import { execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const API = process.env.E2E_API_URL || "http://127.0.0.1:8000";
const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const PYTHON =
  process.env.E2E_PYTHON ||
  [join(REPO, "venv", "Scripts", "python.exe"), join(REPO, "venv", "bin", "python")].find(existsSync) ||
  "python";

const id = randomBytes(4).toString("hex");
const email = `e2e-${id}@cogniseek.dev`;
const password = `E2e-${randomBytes(9).toString("base64url")}7`;
const marker = `zephyrquartz${id}`; // a word that exists only in this test's files

let folder = "";

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

  const response = await request.post(`${API}/auth/register`, {
    data: { name: "E2E Smoke", email, password },
  });
  expect(response.ok(), await response.text()).toBe(true);
});

test.afterAll(() => {
  execFileSync(PYTHON, [join(REPO, "scripts", "delete_e2e_user.py"), email], { cwd: REPO, stdio: "inherit" });
  if (folder) rmSync(folder, { recursive: true, force: true });
});

async function expectNoSeriousA11yViolations(page: Page) {
  await page.waitForLoadState("networkidle");
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  const describe = (v: (typeof serious)[number]) =>
    `${v.id}: ${v.help} -> ${v.nodes.map((n) => `${n.target.join(" ")} [${n.failureSummary ?? ""}]`).join("; ")}`;

  expect(serious.map(describe)).toEqual([]);
}

test("log in, index a local folder, search, download, clean up", async ({ page }) => {
  // Log in through the UI.
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/welcome$/); // nothing indexed yet
  await expectNoSeriousA11yViolations(page);

  // Register the folder and start indexing.
  await page.getByLabel(/Add a folder/).fill(folder);
  await page.getByRole("button", { name: "Add folder" }).click();
  await expect(page.getByRole("list", { name: "Registered folders" })).toContainText("cogniseek-e2e-");
  await page.getByRole("button", { name: "Index local folders" }).click();
  await expect(page.getByText(/Indexing queued: Local storage/)).toBeVisible();

  // Watch the job finish on the Indexing page.
  await page.getByRole("link", { name: "Indexing" }).first().click();
  const local = page.locator("section", { has: page.getByRole("heading", { name: "Local storage" }) });
  await expect(local.getByText("Completed", { exact: true }).first()).toBeVisible({ timeout: 150_000 });
  await expect(local.getByText("Indexed", { exact: true }).first().locator("..")).toContainText("3");
  await expectNoSeriousA11yViolations(page);

  // Search for the word only this test's file contains.
  await page.getByRole("link", { name: "Search" }).first().click();
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

  // Log out.
  await page.getByRole("button", { name: "Log out" }).first().click();
  await expect(page).toHaveURL(/\/login$/);
});
