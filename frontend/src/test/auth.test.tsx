import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { TOKEN_KEY } from "../api/client";
import { renderApp } from "./render";
import { api, server } from "./server";

describe("login / logout", () => {
  it("logs in, stores the token and lands on search", async () => {
    let body: unknown;
    server.use(
      http.post(api("/auth/login"), async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ access_token: "fresh-token", token_type: "bearer" });
      }),
    );
    const { user } = renderApp({ route: "/login", loggedIn: false });

    await user.click(screen.getByRole("button", { name: "Sign In with Email" }));
    await user.type(await screen.findByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "secret123");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/search"));
    expect(body).toEqual({ email: "test@example.com", password: "secret123" });
    expect(localStorage.getItem(TOKEN_KEY)).toBe("fresh-token");
    expect(await screen.findByText("Test User")).toBeInTheDocument();
  });

  it("shows the backend's message when the login fails", async () => {
    server.use(
      http.post(api("/auth/login"), () =>
        HttpResponse.json({ detail: "Invalid email or password." }, { status: 401 }),
      ),
    );
    const { user } = renderApp({ route: "/login", loggedIn: false });

    await user.click(screen.getByRole("button", { name: "Sign In with Email" }));
    await user.type(await screen.findByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-pass1");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
    expect(screen.getByTestId("location")).toHaveTextContent("/login");
  });

  it("shows 422 validation messages when registering", async () => {
    server.use(
      http.post(api("/auth/register"), () =>
        HttpResponse.json(
          { detail: [{ msg: "Value error, Password must contain at least one letter and one digit." }] },
          { status: 422 },
        ),
      ),
    );
    const { user } = renderApp({ route: "/login", loggedIn: false });

    await user.click(screen.getByRole("button", { name: "Create Account" }));
    await user.type(await screen.findByLabelText("Full Name"), "New");
    await user.type(await screen.findByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Password"), "abcdefgh");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Password must contain at least one letter and one digit.",
    );
  });

  it("logs out: revokes on the server, clears the token, returns to login", async () => {
    let revoked = false;
    server.use(
      http.post(api("/auth/logout"), () => {
        revoked = true;
        return HttpResponse.json({ status: "success" });
      }),
    );
    const { user } = renderApp();

    await user.click(await screen.findAllByRole("button", { name: "Log out" }).then((b) => b[0]));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/login"));
    expect(revoked).toBe(true);
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("redirects to login when not logged in", async () => {
    renderApp({ route: "/platforms", loggedIn: false });

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/login"));
  });

  it("a 401 from any API call ends the session and says so", async () => {
    server.use(
      http.get(api("/dashboard/stats"), () => HttpResponse.json({ detail: "expired" }, { status: 401 })),
    );
    renderApp();

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/login"));
    expect(await screen.findByText("Your session has expired. Please log in again.")).toBeInTheDocument();
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});
