// Display helpers. Every function returns "—" for unknown values rather than inventing one.

export const UNKNOWN = "—";

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || Number.isNaN(bytes)) return UNKNOWN;
  if (bytes < 1024) return `${bytes} B`;

  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let unit = 0;

  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }

  return `${value >= 10 ? Math.round(value) : value.toFixed(1)} ${units[unit]}`;
}

/** Backend datetimes without a zone are UTC. */
export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;

  const hasZone = /[zZ]|[+-]\d\d:?\d\d$/.test(value);
  const date = new Date(hasZone ? value : `${value}Z`);

  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDate(value: string | null | undefined): string {
  const date = parseDate(value);
  return date
    ? date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
    : UNKNOWN;
}

export function formatDateTime(value: string | null | undefined): string {
  const date = parseDate(value);
  return date ? date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : UNKNOWN;
}

export function formatRelative(value: string | null | undefined, now: Date = new Date()): string {
  const date = parseDate(value);
  if (!date) return UNKNOWN;

  const seconds = Math.round((now.getTime() - date.getTime()) / 1000);

  if (seconds < 45) return "just now";
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
  if (seconds < 86_400) return `${Math.round(seconds / 3600)} h ago`;
  if (seconds < 7 * 86_400) return `${Math.round(seconds / 86_400)} d ago`;

  return formatDate(value);
}

export function formatDuration(
  start: string | null | undefined,
  end: string | null | undefined,
  now = new Date(),
): string {
  const from = parseDate(start);
  if (!from) return UNKNOWN;

  const to = parseDate(end) ?? now;
  const seconds = Math.max(0, Math.round((to.getTime() - from.getTime()) / 1000));

  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;

  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

export type MatchLevel = "Strong" | "Good" | "Partial";

/**
 * Score in [0, 1] -> 3 levels + the exact percentage. Every returned result
 * already passed an evidence gate, so the lowest level is "Partial", not
 * "irrelevant". Scale (backend noisy-OR): a full file-name match alone is 0.70,
 * a clear visual (CLIP) match alone about 0.30-0.50, several signals together
 * approach 1.
 */
export function relevance(score: number): { level: MatchLevel; percent: number } {
  const percent = Math.round(Math.max(0, Math.min(1, score)) * 100);
  const level: MatchLevel = percent >= 60 ? "Strong" : percent >= 30 ? "Good" : "Partial";

  return { level, percent };
}

/** Split text into plain and highlighted parts from [start, end) offsets (no HTML injection). */
export function highlightParts(text: string, ranges: number[][]): { text: string; mark: boolean }[] {
  const valid = ranges
    .filter((r) => r.length === 2 && r[0] >= 0 && r[1] > r[0] && r[0] < text.length)
    .map(([start, end]) => [start, Math.min(end, text.length)] as const)
    .sort((a, b) => a[0] - b[0]);

  const parts: { text: string; mark: boolean }[] = [];
  let cursor = 0;

  for (const [start, end] of valid) {
    if (start < cursor) continue; // overlapping range
    if (start > cursor) parts.push({ text: text.slice(cursor, start), mark: false });
    parts.push({ text: text.slice(start, end), mark: true });
    cursor = end;
  }

  if (cursor < text.length) parts.push({ text: text.slice(cursor), mark: false });

  return parts;
}
