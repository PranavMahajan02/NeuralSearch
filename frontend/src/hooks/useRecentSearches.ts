import { useCallback, useState } from "react";

const MAX = 8;

function storageKey(userId: string): string {
  return `cogniseek_recent_searches_${userId}`;
}

function read(userId: string): string[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(storageKey(userId)) ?? "[]");
    return Array.isArray(parsed)
      ? parsed.filter((q): q is string => typeof q === "string").slice(0, MAX)
      : [];
  } catch {
    return [];
  }
}

/** The user's last 8 queries, kept in this browser only (per user). */
export function useRecentSearches(userId: string) {
  const [items, setItems] = useState<string[]>(() => read(userId));

  const save = useCallback(
    (next: string[]) => {
      setItems(next);
      try {
        localStorage.setItem(storageKey(userId), JSON.stringify(next));
      } catch {
        /* storage full or disabled: keep the in-memory list */
      }
    },
    [userId],
  );

  const add = useCallback(
    (query: string) => {
      const trimmed = query.trim();
      if (!trimmed) return;
      save([trimmed, ...read(userId).filter((q) => q.toLowerCase() !== trimmed.toLowerCase())].slice(0, MAX));
    },
    [save, userId],
  );

  const clear = useCallback(() => save([]), [save]);

  return { items, add, clear };
}
