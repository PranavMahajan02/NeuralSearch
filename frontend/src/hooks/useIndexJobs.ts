import { useCallback, useEffect, useRef, useState } from "react";
import { getIndexJobs, IndexJob, isActive } from "../services/index";

// The ONE poller for /index/jobs (FE-08 had two, each every second).
export const ACTIVE_POLL_MS = 2000;
export const IDLE_POLL_MS = 15000;

/**
 * Polls /index/jobs every 2 s while any job is queued or running and every
 * 15 s otherwise. `refresh()` fetches immediately (e.g. after starting or
 * cancelling a job) and re-arms the timer.
 */
export function useIndexJobs(enabled: boolean) {
  const [jobs, setJobs] = useState<IndexJob[]>([]);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inFlight = useRef(false);
  const alive = useRef(true);

  const schedule = useCallback((delay: number, run: () => void) => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(run, delay);
  }, []);

  const refresh = useCallback(async () => {
    if (!enabled || inFlight.current) return;
    inFlight.current = true;

    let next = IDLE_POLL_MS;

    try {
      const latest = await getIndexJobs();
      if (!alive.current) return;
      setJobs(latest);
      next = latest.some(isActive) ? ACTIVE_POLL_MS : IDLE_POLL_MS;
    } catch (error) {
      console.error("Polling /index/jobs failed:", error);
    } finally {
      inFlight.current = false;
      if (alive.current && enabled) schedule(next, () => void refresh());
    }
  }, [enabled, schedule]);

  useEffect(() => {
    alive.current = true;

    if (enabled) {
      void refresh();
    } else {
      setJobs([]);
    }

    return () => {
      alive.current = false;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [enabled, refresh]);

  return { jobs, refresh };
}
