// Every interval the UI waits on, in one place. Read at call time, so tests can
// shorten them (src/test/setup.ts) instead of depending on wall-clock speed.
export const DEFAULT_TIMING = {
  /** /index/jobs refetch while a job is queued or running (stopped when idle). */
  jobsPollMs: 2000,
  /** Stats + recently indexed refetch while a job runs. */
  liveCountsMs: 3000,
  /** Filter changes re-run the search after this pause. */
  filterDebounceMs: 250,
};

export const timing = { ...DEFAULT_TIMING };
