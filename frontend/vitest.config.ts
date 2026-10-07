import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
    // Ceilings, not delays: integration tests (several typed fields + MSW round trips)
    // must not fail just because a loaded machine is slow.
    testTimeout: 30_000,
    hookTimeout: 30_000,
    // Leave CPU for the system under load: oversubscribed workers starve Vitest's own RPC.
    maxWorkers: 4,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/test/**",
        "src/api/schema.d.ts",
        "src/main.tsx",
        "src/vite-env.d.ts",
      ],
      reporter: ["text-summary", "text", "html"],
      thresholds: { statements: 70, branches: 70, functions: 70, lines: 70 },
    },
  },
});
