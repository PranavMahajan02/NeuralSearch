# CogniSeek frontend

React 19 + TypeScript + Vite + Tailwind. See the main [README](../README.md#frontend) for commands,
tests and the end-to-end smoke test.

```
src/
  api/          client.ts (fetch + errors), schema.d.ts (generated), types.ts, endpoints.ts, queries.ts
  auth/         AuthContext (token, profile, 401 handling), RequireAuth
  components/   common/ (Modal, Toast, Button, …), layout/AppShell, search/, platforms/, indexing/
  hooks/        useSearch, useOpenFile, usePlatformActions, useRecentSearches, …
  pages/        Login, Search, Platforms, Indexing, Welcome, RootRedirect
  test/         MSW server, render helpers, *.test.tsx
e2e/            Playwright smoke test, screenshot script
```
