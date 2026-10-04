import { apiJson } from "./http";

export async function searchFiles(
  query: string,
  platform: string = "all",
  searchType: string = "all"
) {
  const data = await apiJson<{ results: any[] }>("/search/", {
    method: "POST",
    json: { query, platform, search_type: searchType },
    errorMessage: "Search failed.",
  });

  return data.results;
}
