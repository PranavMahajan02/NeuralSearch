import "@testing-library/jest-dom/vitest";
import { cleanup, configure } from "@testing-library/react";
import { focusManager, onlineManager } from "@tanstack/react-query";
import { MotionGlobalConfig } from "motion/react";
import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";

import { DEFAULT_TIMING, timing } from "../lib/timing";
import { server } from "./server";

// findBy*/waitFor give up after 5 s (a ceiling, not a delay): a loaded CI machine
// must not fail a test that is merely slow.
configure({ asyncUtilTimeout: 5000 });

// No animation runs in tests: nothing waits on a JS-driven fade or exit.
MotionGlobalConfig.skipAnimations = true;

// Short, deterministic intervals instead of wall-clock ones (2 s poller, 3 s live counts, 250 ms debounce).
export const TEST_TIMING = { jobsPollMs: 100, liveCountsMs: 100, filterDebounceMs: 20 };

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));

beforeEach(() => {
  Object.assign(timing, TEST_TIMING);
  localStorage.clear();
  // TanStack's online/focus managers are global singletons: reset them every test.
  onlineManager.setOnline(true);
  focusManager.setFocused(undefined);
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
  localStorage.clear();
  Object.assign(timing, DEFAULT_TIMING);
});

afterAll(() => server.close());

// jsdom lacks these browser APIs.
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }) as MediaQueryList;
}
