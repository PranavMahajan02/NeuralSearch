import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { getToken } from "../api/client";
import { renderApp } from "./render";
import { api, server } from "./server";

async function openSettings() {
  const view = renderApp({ route: "/search" });
  await view.user.click((await screen.findAllByRole("button", { name: "Account settings" }))[0]);
  return { ...view, dialog: screen.getByRole("dialog", { name: "Account settings" }) };
}

describe("account settings", () => {
  it("deletes the account only after typing DELETE and the password, then signs out", async () => {
    let body: unknown;
    server.use(
      http.delete(api("/auth/account"), async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ status: "success", deleted_files: 3, revoked: {} });
      }),
    );
    const { user, dialog } = await openSettings();
    const section = within(within(dialog).getByRole("region", { name: "Delete account" }));
    const submit = section.getByRole("button", { name: "Delete my account" });

    await user.type(section.getByLabelText("Password"), "Password123");
    expect(submit).toBeDisabled();
    await user.type(section.getByLabelText(/Type DELETE/), "delete");
    expect(submit).toBeDisabled(); // exact phrase only
    await user.clear(section.getByLabelText(/Type DELETE/));
    await user.type(section.getByLabelText(/Type DELETE/), "DELETE");
    await user.click(submit);

    expect(await screen.findByText("Your account and all of its data were deleted.")).toBeInTheDocument();
    expect(body).toEqual({ password: "Password123" });
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/login"));
    expect(getToken()).toBeNull();
  });

  it("shows a wrong password without ending the session", async () => {
    server.use(
      http.delete(api("/auth/account"), () =>
        HttpResponse.json({ detail: "Current password is incorrect." }, { status: 403 }),
      ),
    );
    const { user, dialog } = await openSettings();
    const section = within(within(dialog).getByRole("region", { name: "Delete account" }));

    await user.type(section.getByLabelText(/Type DELETE/), "DELETE");
    await user.type(section.getByLabelText("Password"), "nope");
    await user.click(section.getByRole("button", { name: "Delete my account" }));

    expect(await section.findByRole("alert")).toHaveTextContent("Current password is incorrect.");
    expect(screen.getByTestId("location")).toHaveTextContent("/search");
  });

  it("changes the password and signs out", async () => {
    let body: unknown;
    server.use(
      http.post(api("/auth/change-password"), async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ status: "success", message: "ok" });
      }),
    );
    const { user, dialog } = await openSettings();
    const section = within(within(dialog).getByRole("region", { name: "Change password" }));

    await user.type(section.getByLabelText("Current password"), "Password123");
    await user.type(section.getByLabelText("New password"), "Brandnew123");
    await user.click(section.getByRole("button", { name: "Change password" }));

    expect(await screen.findByText("Password changed. Please sign in again.")).toBeInTheDocument();
    expect(body).toEqual({ current_password: "Password123", new_password: "Brandnew123" });
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/login"));
  });

  it("downloads the data export", async () => {
    URL.createObjectURL = vi.fn(() => "blob:fake");
    URL.revokeObjectURL = vi.fn();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const { user, dialog } = await openSettings();

    await user.click(within(dialog).getByRole("button", { name: "Export my data" }));

    expect(await screen.findByText("Your data export is downloading.")).toBeInTheDocument();
    expect(click).toHaveBeenCalled();
  });
});
