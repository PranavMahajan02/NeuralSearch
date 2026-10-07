import type { ReactElement } from "react";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { QueryClient } from "@tanstack/react-query";

import { AppRoutes, Providers } from "../App";
import { TOKEN_KEY } from "../api/client";

/** Shows the current path so tests can assert redirects. */
function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname + location.search}</div>;
}

/** A fresh client per render: no retries, no cache kept between tests. */
export function testQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
}

function renderWith(ui: ReactElement, route: string, loggedIn: boolean) {
  if (loggedIn) localStorage.setItem(TOKEN_KEY, "test-token");

  const client = testQueryClient();
  // delay: null - typing does not yield between keystrokes, so speed does not depend on the CPU.
  const user = userEvent.setup({ delay: null });
  const utils = render(
    <MemoryRouter initialEntries={[route]}>
      <Providers client={client} reducedMotion="always">
        {ui}
        <LocationProbe />
      </Providers>
    </MemoryRouter>,
  );

  return { ...utils, user, client };
}

interface Options {
  route?: string;
  loggedIn?: boolean;
}

/** The whole app (providers + routes) at `route`, optionally with a token. */
export function renderApp({ route = "/search", loggedIn = true }: Options = {}) {
  return renderWith(<AppRoutes />, route, loggedIn);
}

/** A single component inside the providers (logged in). */
export function renderWithProviders(ui: ReactElement, route = "/") {
  return renderWith(
    <Routes>
      <Route path="*" element={ui} />
    </Routes>,
    route,
    true,
  );
}
