import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The dev server binds 127.0.0.1:3000 and FAILS if the port is taken
// (strictPort) instead of silently moving to another port, which would break
// CORS and the OAuth return URL.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: process.env.VITE_HOST || "127.0.0.1",
    port: Number(process.env.VITE_PORT || 3000),
    strictPort: true,
  },
  build: {
    // Never inline assets as data: URIs: the production CSP allows fonts from
    // 'self' only (deploy/caddy/Caddyfile), and small font subsets would be inlined.
    assetsInlineLimit: 0,
    rollupOptions: {
      output: {
        // Long-lived vendor chunks: app changes don't invalidate them.
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          query: ["@tanstack/react-query"],
          motion: ["motion"],
        },
      },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4173,
    strictPort: true,
  },
});
