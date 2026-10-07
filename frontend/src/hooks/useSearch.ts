import { useInfiniteQuery } from "@tanstack/react-query";

import * as api from "../api/endpoints";
import { keys } from "../api/queries";
import type { SearchPlatform, SearchResponse, SearchType } from "../api/types";
import { useAuth } from "../auth/AuthContext";

export const PAGE_SIZE = 20;

export interface SearchParams {
  query: string;
  type: SearchType;
  platform: SearchPlatform;
}

/**
 * Server-side search, paginated with offset/limit ("Load more").
 *
 * Race safety:
 * - every (query, type, platform) has its own cache entry, so a slow response
 *   for an OLD query can only ever land in the old entry - the screen shows
 *   the entry of the CURRENT key, never an out-of-order result;
 * - the request uses TanStack's AbortSignal, so when the key changes the
 *   superseded request is aborted (the fetch is cancelled, not just ignored).
 *
 * Filters are never applied client-side: a type/platform change is a new key,
 * i.e. a new backend query.
 */
export function useSearch({ query, type, platform }: SearchParams) {
  const { userId } = useAuth();
  const trimmed = query.trim();

  return useInfiniteQuery({
    queryKey: keys.search(userId, trimmed, type, platform),
    queryFn: ({ pageParam, signal }) =>
      api.searchFiles(
        { query: trimmed, search_type: type, platform, limit: PAGE_SIZE, offset: pageParam },
        signal,
      ),
    initialPageParam: 0,
    getNextPageParam: (last: SearchResponse) =>
      last.offset + last.results.length < last.total && last.results.length > 0
        ? last.offset + last.results.length
        : undefined,
    enabled: trimmed.length > 0 && userId !== "",
    staleTime: 30_000,
  });
}
