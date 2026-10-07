// MSW: a fake backend for component tests. Handlers mirror the real responses
// (typed with the generated API types); tests override them per case.
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import { API_BASE_URL } from "../api/client";
import type {
  DashboardStats,
  FoldersResponse,
  JobWithHistory,
  RecentResponse,
  SearchResponse,
  SearchResult,
  User,
} from "../api/types";

export const api = (path: string) => new URL(path, API_BASE_URL).toString();

export const USER: User = {
  id: "11111111-1111-1111-1111-111111111111",
  name: "Test User",
  email: "test@example.com",
};

export function makeStats(overrides: Partial<DashboardStats> = {}): DashboardStats {
  return {
    total_files: 12,
    documents: 7,
    images: 3,
    audio: 1,
    video: 1,
    by_platform: { local: 5, google_drive: 7, github: 0 },
    no_content_files: 0,
    failed_files: 0,
    last_indexed_at: "2026-10-07T08:00:00",
    connected_platforms: 2,
    supported_platforms: 3,
    ready_platforms: 2,
    platforms: {
      google_drive: { connected: true, indexed_files: 7, last_indexed_at: "2026-10-07T08:00:00Z" },
      github: { connected: false, indexed_files: 0, last_indexed_at: null },
      local: {
        connected: true,
        indexed_files: 5,
        last_indexed_at: "2026-10-06T08:00:00Z",
        folders: ["C:\\docs"],
      },
    },
    ...overrides,
  };
}

export function makeResult(overrides: Partial<SearchResult> = {}): SearchResult {
  return {
    platform: "local",
    source_id: "c:\\docs\\java notes.pdf",
    type: "document",
    file: "java notes.pdf",
    display_path: "C:\\docs\\java notes.pdf",
    path: "C:\\docs\\java notes.pdf",
    score: 0.82,
    match: {
      reasons: ["filename", "content"],
      field: "content",
      snippet: "Notes about Java streams",
      highlights: [[12, 16]],
    },
    file_size: 2048,
    modified_at: "2026-10-01T10:00:00Z",
    mime_type: "application/pdf",
    extension: "pdf",
    ...overrides,
  };
}

export function searchResponse(results: SearchResult[], extra: Partial<SearchResponse> = {}): SearchResponse {
  return {
    query: "q",
    platform: "all",
    search_type: "all",
    limit: 20,
    offset: 0,
    total: results.length,
    results,
    ...extra,
  };
}

export function makeJob(overrides: Partial<JobWithHistory> = {}): JobWithHistory {
  return {
    id: "job-1",
    platform: "local",
    status: "completed",
    total_files: 10,
    processed_files: 10,
    succeeded_files: 9,
    failed_files: 1,
    skipped_files: 2,
    downloaded_files: 0,
    indexed_files: 10,
    progress: 100,
    current_file: "",
    error_message: null,
    cancel_requested: false,
    created_at: "2026-10-07T08:00:00",
    started_at: "2026-10-07T08:00:00",
    completed_at: "2026-10-07T08:01:05",
    heartbeat_at: null,
    indexed: true,
    history: [],
    ...overrides,
  };
}

const folders: FoldersResponse = { folders: ["C:\\docs"], picker_available: false };
const recent: RecentResponse = {
  files: [
    {
      platform: "local",
      source_id: "c:\\docs\\a.pdf",
      file: "a.pdf",
      display_path: "C:\\docs\\a.pdf",
      type: "document",
      indexed_at: "2026-10-07T08:00:00Z",
    },
  ],
};

export const handlers = [
  http.get(api("/auth/profile"), () => HttpResponse.json(USER)),
  http.get(api("/auth/login-state"), () => HttpResponse.json({ has_indexed: true, platforms: ["local"] })),
  http.post(api("/auth/logout"), () => HttpResponse.json({ status: "success" })),
  http.get(api("/search/health"), () => HttpResponse.json({ status: "Search API Ready" })),
  http.get(api("/dashboard/stats"), () => HttpResponse.json(makeStats())),
  http.get(api("/dashboard/recent"), () => HttpResponse.json(recent)),
  http.get(api("/index/jobs"), () => HttpResponse.json([makeJob()])),
  http.get(api("/platforms/local/folders"), () => HttpResponse.json(folders)),
  http.get(api("/platforms/google-drive/status"), () =>
    HttpResponse.json({ connected: true, account_email: "me@example.com" }),
  ),
  http.get(api("/platforms/github/status"), () =>
    HttpResponse.json({ connected: false, account_name: null }),
  ),
  http.get(api("/search/suggestions"), () => HttpResponse.json({ prefix: "", suggestions: [] })),
  http.post(api("/search/"), () => HttpResponse.json(searchResponse([makeResult()]))),
];

export const server = setupServer(...handlers);
