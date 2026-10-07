import { useState } from "react";
import { AlertTriangle, SearchX } from "lucide-react";

import { ApiError } from "../../api/client";
import type { SearchResult } from "../../api/types";
import { useOpenFile } from "../../hooks/useOpenFile";
import type { useSearch } from "../../hooks/useSearch";
import { Button } from "../common/Button";
import { Skeleton, Spinner } from "../common/Spinner";
import { ResultCard } from "./ResultCard";
import { ResultDetailsModal } from "./ResultDetailsModal";

type SearchState = ReturnType<typeof useSearch>;

export function ResultSkeletons() {
  return (
    <div aria-busy="true" aria-label="Loading results" className="space-y-3">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
        >
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="mt-3 h-3 w-2/3" />
          <Skeleton className="mt-2 h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}

interface ResultListProps {
  search: SearchState;
  query: string;
  filtered: boolean;
  onClearFilters: () => void;
}

export function ResultList({ search, query, filtered, onClearFilters }: ResultListProps) {
  const { open, busyId } = useOpenFile();
  const [details, setDetails] = useState<SearchResult | null>(null);

  if (search.isPending) return <ResultSkeletons />;

  if (search.isError) {
    const error = search.error;
    const message = error instanceof ApiError ? error.message : "Search failed.";

    return (
      <div
        role="alert"
        className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-rose-950 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-100"
      >
        <div className="flex items-start gap-3">
          <AlertTriangle aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
          <div className="space-y-3">
            <p className="font-semibold">The search could not be completed.</p>
            <p className="text-sm">{message}</p>
            <Button onClick={() => void search.refetch()}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  const pages = search.data.pages;
  const total = pages[0]?.total ?? 0;
  // The backend may return the same file on two pages if the index changed between them.
  const seen = new Set<string>();
  const results = pages
    .flatMap((page) => page.results)
    .filter((r) => {
      const key = `${r.platform}:${r.source_id}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

  if (total === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-700">
        <SearchX aria-hidden="true" className="mx-auto h-8 w-8 text-slate-500" />
        <p className="mt-3 font-semibold">No results for “{query}”</p>
        <ul className="mt-2 space-y-1 text-sm text-slate-600 dark:text-slate-400">
          <li>Check the spelling, or try fewer or more general words.</li>
          <li>Describe what an image shows (e.g. “dog on a beach”).</li>
          <li>Make sure the platform holding the file has been indexed.</li>
        </ul>
        {filtered && (
          <Button className="mt-4" onClick={onClearFilters}>
            Search all types and platforms
          </Button>
        )}
      </div>
    );
  }

  return (
    <section aria-label="Search results" className="space-y-3">
      <p className="text-sm text-slate-600 dark:text-slate-400" aria-live="polite">
        {total === 1 ? "1 result" : `${total} results`} · showing {results.length}
        {search.isFetching && !search.isFetchingNextPage && <Spinner className="ml-2 align-middle" />}
      </p>
      <ol className="space-y-3">
        {results.map((result) => (
          <li key={`${result.platform}:${result.source_id}`}>
            <ResultCard
              result={result}
              opening={busyId === result.source_id}
              onOpen={(r) => void open(r)}
              onDetails={setDetails}
            />
          </li>
        ))}
      </ol>
      {search.hasNextPage && (
        <div className="flex justify-center pt-2">
          <Button onClick={() => void search.fetchNextPage()} disabled={search.isFetchingNextPage}>
            {search.isFetchingNextPage ? (
              <Spinner label="Loading…" />
            ) : (
              `Load more (${total - results.length} left)`
            )}
          </Button>
        </div>
      )}
      {details && (
        <ResultDetailsModal
          result={details}
          opening={busyId === details.source_id}
          onOpen={(r) => void open(r)}
          onClose={() => setDetails(null)}
        />
      )}
    </section>
  );
}
