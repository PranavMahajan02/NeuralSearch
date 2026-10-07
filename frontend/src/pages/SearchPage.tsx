import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import type { SearchPlatform, SearchType } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { FilterBar } from "../components/search/FilterBar";
import { RecentPanel } from "../components/search/RecentPanel";
import { ResultList } from "../components/search/ResultList";
import { SearchBar } from "../components/search/SearchBar";
import { StatsGrid } from "../components/search/StatsGrid";
import { useDebounced } from "../hooks/useDebounced";
import { useRecentSearches } from "../hooks/useRecentSearches";
import { useSearch } from "../hooks/useSearch";

const TYPES: SearchType[] = ["all", "document", "image", "audio", "video"];
const PLATFORMS: SearchPlatform[] = ["all", "local", "google_drive", "github"];

export const FILTER_DEBOUNCE_MS = 250;

function pick<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}

/**
 * The search state lives in the URL (?q=&type=&platform=), so back/forward and
 * reload work. Filter changes re-run the search on the server after 250 ms.
 */
export function SearchPage() {
  const { userId } = useAuth();
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const type = pick(params.get("type"), TYPES, "all");
  const platform = pick(params.get("platform"), PLATFORMS, "all");

  const [draft, setDraft] = useState(query);
  const recentSearches = useRecentSearches(userId);

  // Keep the box in sync when the URL query changes (back/forward, recent search).
  const [shownQuery, setShownQuery] = useState(query);
  if (query !== shownQuery) {
    setShownQuery(query);
    setDraft(query);
  }

  // Debounce a primitive key (an object literal would be a new value every render).
  const [debouncedType, debouncedPlatform] = useDebounced(`${type}|${platform}`, FILTER_DEBOUNCE_MS).split(
    "|",
  ) as [SearchType, SearchPlatform];
  const search = useSearch({ query, type: debouncedType, platform: debouncedPlatform });

  const update = (next: Partial<{ q: string; type: SearchType; platform: SearchPlatform }>) => {
    const merged = { q: query, type, platform, ...next };
    const out = new URLSearchParams();
    if (merged.q) out.set("q", merged.q);
    if (merged.type !== "all") out.set("type", merged.type);
    if (merged.platform !== "all") out.set("platform", merged.platform);
    setParams(out);
  };

  const runSearch = (q: string) => {
    recentSearches.add(q);
    update({ q });
  };

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <SearchBar value={draft} onChange={setDraft} onSubmit={runSearch} />
        <FilterBar
          type={type}
          platform={platform}
          onTypeChange={(t) => update({ type: t })}
          onPlatformChange={(p) => update({ platform: p })}
        />
      </div>

      {query ? (
        <ResultList
          search={search}
          query={query}
          filtered={type !== "all" || platform !== "all"}
          onClearFilters={() => update({ type: "all", platform: "all" })}
        />
      ) : (
        <div className="space-y-6">
          <StatsGrid />
          <RecentPanel
            searches={recentSearches.items}
            onSearch={(q) => {
              setDraft(q);
              runSearch(q);
            }}
            onClearSearches={recentSearches.clear}
          />
        </div>
      )}
    </div>
  );
}
