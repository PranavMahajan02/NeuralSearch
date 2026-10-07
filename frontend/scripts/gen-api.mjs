// Generates src/api/schema.d.ts from the backend's OpenAPI document.
// Source: $OPENAPI_URL (a URL or a file path), default http://127.0.0.1:8000/openapi.json
// (the backend serves /openapi.json in development).
import { execFileSync } from "node:child_process";

const source = process.env.OPENAPI_URL || "http://127.0.0.1:8000/openapi.json";

execFileSync(
  process.execPath,
  ["node_modules/openapi-typescript/bin/cli.js", source, "-o", "src/api/schema.d.ts"],
  { stdio: "inherit" },
);
