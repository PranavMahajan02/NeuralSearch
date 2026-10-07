import type { ReactElement } from "react";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { AppRoutes, Providers } from "../App";
import { TOKEN_KEY } from "../api/client";
import { createQueryClient } from "../api/queries";

/** Shows the current path so tests can assert redirects. */
function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname + location.search}</div>;
}

interface Options {
  route?: string;
  loggedIn?: boolean;
}

/** The whole app (providers + routes) at `route`, optionally with a token. */
export function renderApp({ route = "/search", loggedIn = true }: Options = {}) {
  if (loggedIn) localStorage.setItem(TOKEN_KEY, "test-token");

  const client = createQueryClient();
  client.setDefaultOptions({ queries: { ...client.getDefaultOptions().queries, retry: false } });

  const user = userEvent.setup();
  const utils = render(
    <MemoryRouter initialEntries={[route]}>
      <Providers client={client}>
        <AppRoutes />
        <LocationProbe />
      </Providers>
    </MemoryRouter>,
  );

  return { ...utils, user, client };
}

/** A single component inside the providers (logged in). */
export function renderWithProviders(ui: ReactElement, route = "/") {
  localStorage.setItem(TOKEN_KEY, "test-token");
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { ...client.getDefaultOptions().queries, retry: false } });
  const user = userEvent.setup();

  const utils = render(
    <MemoryRouter initialEntries={[route]}>
      <Providers client={client}>
        <Routes>
          <Route path="*" element={ui} />
        </Routes>
        <LocationProbe />
      </Providers>
    </MemoryRouter>,
  );

  return { ...utils, user, client };
}
