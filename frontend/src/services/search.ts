import { apiJson } from "./http";

export type SearchMatch = {
  reasons: string[];
  field: "content" | "ocr" | "transcript" | "filename";
  snippet: string;
  /** [start, end) character offsets into `snippet` of the matched terms. */
  highlights: [number, number][];
};

export type SearchResult = {
  platform: "local" | "google_drive" | "github";
  source_id: string;
  type: "document" | "image" | "audio" | "video";
  file: string;
  display_path: string;
  path: string;
  /** 0..1, comparable across types. */
  score: number;
  owner?: string;
  repo?: string;
  match: SearchMatch;
};

export type SearchResponse = {
  query: string;
  platform: string;
  search_type: string;
  limit: number;
  offset: number;
  total: number;
  results: SearchResult[];
};

export async function searchFiles(
  query: string,
  platform: string = "all",
  searchType: string = "all",
  limit: number = 20,
  offset: number = 0
): Promise<SearchResponse> {
  return apiJson<SearchResponse>("/search/", {
    method: "POST",
    json: { query, platform, search_type: searchType, limit, offset },
    errorMessage: "Search failed.",
  });
}
