import { screen, waitFor, within } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { SearchRequest } from "../api/types";
import { renderApp } from "./render";
import { api, makeResult, searchResponse, server } from "./server";

function captureSearches() {
  const bodies: SearchRequest[] = [];
  return {
    bodies,
    handler: (respond: (body: SearchRequest) => Response | Promise<Response>) =>
      http.post(api("/search/"), async ({ request }) => {
        const body = (await request.json()) as SearchRequest;
        bodies.push(body);
        return respond(body);
      }),
  };
}

describe("search", () => {
  it("shows real results: score, platform, path, size, date, highlighted snippet, reasons", async () => {
    renderApp({ route: "/search?q=java" });

    const card = (await screen.findByRole("heading", { name: "java notes.pdf" })).closest("article")!;
    const scope = within(card);

    expect(scope.getByText(/Strong/)).toHaveTextContent("Strong · 82%");
    expect(scope.getByText("Local storage")).toBeInTheDocument();
    expect(scope.getByText("C:\\docs\\java notes.pdf")).toBeInTheDocument();
    expect(scope.getByText("2.0 KB")).toBeInTheDocument();
    expect(scope.getByText(/Modified/)).toBeInTheDocument();
    // Highlight from the API offsets [12, 16) of "Notes about Java streams".
    expect(card.querySelector("mark")).toHaveTextContent("Java");
    expect(scope.getByRole("list", { name: "Why it matched" })).toHaveTextContent("File nameText");
    expect(screen.getByText(/1 result/)).toBeInTheDocument();
  });

  it("shows unknown metadata as a dash, never a made-up value", async () => {
    server.use(
      http.post(api("/search/"), () =>
        HttpResponse.json(searchResponse([makeResult({ file_size: null, modified_at: null })])),
      ),
    );
    renderApp({ route: "/search?q=java" });

    const card = (await screen.findByRole("heading", { name: "java notes.pdf" })).closest("article")!;
    expect(within(card).getByText("—")).toBeInTheDocument();
    expect(within(card).getByText("Modified —")).toBeInTheDocument();
  });

  it("shows an empty state with suggestions", async () => {
    server.use(http.post(api("/search/"), () => HttpResponse.json(searchResponse([]))));
    renderApp({ route: "/search?q=zzzz&type=image" });

    expect(await screen.findByText("No results for “zzzz”")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Search all types and platforms" })).toBeInTheDocument();
  });

  it("shows the backend detail on an error and retries", async () => {
    let calls = 0;
    server.use(
      http.post(api("/search/"), () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({ detail: "Search is temporarily unavailable." }, { status: 503 })
          : HttpResponse.json(searchResponse([makeResult()]));
      }),
    );
    const { user } = renderApp({ route: "/search?q=java" });

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Search is temporarily unavailable.");

    await user.click(within(alert).getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { name: "java notes.pdf" })).toBeInTheDocument();
  });

  it("shows a 422 validation message instead of [object Object]", async () => {
    server.use(
      http.post(api("/search/"), () =>
        HttpResponse.json(
          { detail: [{ msg: "String should have at most 500 characters" }] },
          { status: 422 },
        ),
      ),
    );
    renderApp({ route: "/search?q=x" });

    expect(await screen.findByRole("alert")).toHaveTextContent("String should have at most 500 characters");
  });

  it("re-runs the search on the server when a filter changes (no client-side filtering)", async () => {
    const searches = captureSearches();
    server.use(
      searches.handler((body) =>
        HttpResponse.json(
          searchResponse(
            body.search_type === "image"
              ? [makeResult({ file: "dog.jpg", source_id: "dog", type: "image" })]
              : [makeResult()],
          ),
        ),
      ),
    );
    const { user } = renderApp({ route: "/search?q=pets" });

    expect(await screen.findByRole("heading", { name: "java notes.pdf" })).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "Images" }));

    expect(await screen.findByRole("heading", { name: "dog.jpg" })).toBeInTheDocument();
    expect(searches.bodies.map((b) => b.search_type)).toEqual(["all", "image"]);
    expect(screen.queryByRole("heading", { name: "java notes.pdf" })).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Platform"), "github");
    await waitFor(() =>
      expect(searches.bodies.at(-1)).toMatchObject({ search_type: "image", platform: "github" }),
    );
  });

  it("aborts the superseded request and never shows an out-of-order response", async () => {
    let slowAborted = false;
    server.use(
      http.post(api("/search/"), async ({ request }) => {
        const body = (await request.json()) as SearchRequest;
        if (body.query === "old") {
          request.signal.addEventListener("abort", () => (slowAborted = true));
          await delay(300); // arrives AFTER the newer query's response
          return HttpResponse.json(searchResponse([makeResult({ file: "old.pdf", source_id: "old" })]));
        }
        return HttpResponse.json(searchResponse([makeResult({ file: "new.pdf", source_id: "new" })]));
      }),
    );
    const { user } = renderApp({ route: "/search?q=old" });

    const box = await screen.findByRole("combobox", { name: "Search your files" });
    await user.clear(box);
    await user.type(box, "new{Enter}");

    expect(await screen.findByRole("heading", { name: "new.pdf" })).toBeInTheDocument();
    await delay(400);

    expect(screen.queryByRole("heading", { name: "old.pdf" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "new.pdf" })).toBeInTheDocument();
    expect(slowAborted).toBe(true);
  });

  it("loads more results with offset/limit", async () => {
    const searches = captureSearches();
    const page = (offset: number, count: number) =>
      Array.from({ length: count }, (_, i) =>
        makeResult({ file: `file ${offset + i}.pdf`, source_id: `s${offset + i}` }),
      );
    server.use(
      searches.handler((body) =>
        HttpResponse.json(
          searchResponse(page(body.offset, body.offset === 0 ? 20 : 5), { total: 25, offset: body.offset }),
        ),
      ),
    );
    const { user } = renderApp({ route: "/search?q=files" });

    expect(await screen.findByText(/25 results · showing 20/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Load more (5 left)" }));

    expect(await screen.findByRole("heading", { name: "file 24.pdf" })).toBeInTheDocument();
    expect(screen.getByText(/25 results · showing 25/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Load more/ })).not.toBeInTheDocument();
    expect(searches.bodies.map((b) => [b.offset, b.limit])).toEqual([
      [0, 20],
      [20, 20],
    ]);
  });

  it("stores recent searches in this browser and can clear them", async () => {
    const { user } = renderApp({ route: "/search" });

    await user.type(await screen.findByRole("combobox", { name: "Search your files" }), "java{Enter}");
    await screen.findByRole("heading", { name: "java notes.pdf" });

    await user.clear(screen.getByRole("combobox", { name: "Search your files" }));
    await user.type(screen.getByRole("combobox", { name: "Search your files" }), " {Enter}");
    // Back to the start page (no query): the recent search is listed.
    await user.click(screen.getByRole("link", { name: "Search" }));
    expect(await screen.findByRole("button", { name: "java" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.queryByRole("button", { name: "java" })).not.toBeInTheDocument();
  });
});
