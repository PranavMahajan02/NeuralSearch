import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useJobs } from "../api/queries";
import type { SearchPlatform, SearchType } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { HeroLogo } from "../components/common/Brand";
import { FilterBar } from "../components/search/FilterBar";
import { PriorityBanner } from "../components/search/PriorityBanner";
import { RecentPanel } from "../components/search/RecentPanel";
import { ResultList } from "../components/search/ResultList";
import { SearchBar } from "../components/search/SearchBar";
import { StatsGrid } from "../components/search/StatsGrid";
import { useDebounced } from "../hooks/useDebounced";
import { useRecentSearches } from "../hooks/useRecentSearches";
import { useSearch } from "../hooks/useSearch";
import { priorityProgress } from "../lib/indexing";

const TYPES: SearchType[] = ["all", "document", "image", "audio", "video"];
const PLATFORMS: SearchPlatform[] = ["all", "local", "google_drive", "github"];

export const FILTER_DEBOUNCE_MS = 250;

function pick<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback;
}

/**
 * The search state lives in the URL (?q=&type=&platform=), so back/forward and
 * reload work. Filter changes re-run the search on the server after 250 ms.
 *
 * While the priority platform is still indexing, the Platform filter defaults
 * to it (its results are complete first); afterwards the default is All. An
 * explicit choice in the URL always wins.
 */
export function SearchPage() {
  const { userId } = useAuth();
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const type = pick(params.get("type"), TYPES, "all");
  const jobs = useJobs();
  const progress = jobs.data ? priorityProgress(jobs.data) : null;
  const defaultPlatform: SearchPlatform =
    progress && !progress.priorityDone ? (progress.priority.platform as SearchPlatform) : "all";
  const platform = pick(params.get("platform"), PLATFORMS, defaultPlatform);

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
    if (next.platform !== undefined || params.has("platform")) {
      if (merged.platform !== defaultPlatform || params.has("platform")) out.set("platform", merged.platform);
    }
    setParams(out);
  };

  const runSearch = (q: string) => {
    recentSearches.add(q);
    update({ q });
  };

  return (
    <div className="space-y-6">
      {!query && (
        <div className="mx-auto max-w-xl py-10 text-center">
          <HeroLogo />
          <h2 className="font-display text-3xl font-bold leading-none tracking-tight text-slate-800 dark:text-white">
            Search across your world
          </h2>
          <p className="mx-auto mt-2 max-w-sm text-xs text-slate-600 dark:text-slate-400">
            One search over your local files, Google Drive and GitHub: documents, code, images, audio and
            video.
          </p>
        </div>
      )}
      <div className="space-y-3">
        <SearchBar value={draft} onChange={setDraft} onSubmit={runSearch} />
        <FilterBar
          type={type}
          platform={platform}
          onTypeChange={(t) => update({ type: t })}
          onPlatformChange={(p) => update({ platform: p })}
        />
      </div>

      {progress && <PriorityBanner progress={progress} />}

      {query ? (
        <ResultList
          search={search}
          query={query}
          filtered={type !== "all" || platform !== "all"}
          onClearFilters={() => update({ type: "all", platform: "all" })}
        />
      ) : (
        <div className="mx-auto max-w-3xl space-y-6">
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
