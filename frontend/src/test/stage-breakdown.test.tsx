import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { stageRows } from "../components/indexing/StageBreakdown";
import { renderApp } from "./render";
import { api, makeJob, server } from "./server";

const TIMINGS = {
  seconds: { extract_text: 23.1, ocr: 212.4, whisper: 31.3, frame_extract: 35.9, ledger: 0.9, other: 0.2 },
  calls: {},
  by_type: {},
};

describe("where the time went", () => {
  it("lists the stages largest first and folds tiny ones into Other", () => {
    const rows = stageRows(TIMINGS);

    expect(rows.map((r) => r.label)).toEqual([
      "OCR",
      "Video frames",
      "Speech-to-text",
      "Text extraction",
      "Other",
    ]);
    expect(rows.at(-1)?.seconds).toBeCloseTo(1.1); // ledger 0.9 (<0.5%) + other 0.2
    expect(stageRows(null)).toEqual([]);
    expect(stageRows({ seconds: {}, calls: {}, by_type: {} })).toEqual([]);
  });

  it("shows the breakdown of the latest finished job in the Indexing Center", async () => {
    server.use(
      http.get(api("/index/jobs"), () =>
        HttpResponse.json([makeJob({ status: "completed", stage_timings: TIMINGS })]),
      ),
    );
    const { user } = renderApp({ route: "/indexing" });

    const card = (await screen.findByRole("heading", { name: "Local Storage" })).closest("section")!;
    await user.click(within(card).getByText("Where the time went"));

    const list = within(card).getByRole("list", { name: "Time per indexing stage" });
    const items = within(list).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("OCR");
    expect(items[0]).toHaveTextContent("3 min 32 s");
    expect(items[0]).toHaveTextContent("(70%)");
  });

  it("is not shown while the job is still running", async () => {
    server.use(
      http.get(api("/index/jobs"), () =>
        HttpResponse.json([makeJob({ status: "running", completed_at: null, stage_timings: TIMINGS })]),
      ),
    );
    renderApp({ route: "/indexing" });

    await screen.findByRole("progressbar");
    expect(screen.queryByText("Where the time went")).not.toBeInTheDocument();
  });
});
