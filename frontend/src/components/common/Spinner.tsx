import { Loader2 } from "lucide-react";

export function Spinner({ label, className = "" }: { label?: string; className?: string }) {
  return (
    <span role="status" className={`inline-flex items-center gap-2 ${className}`}>
      <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
      {label ? <span>{label}</span> : <span className="sr-only">Loading</span>}
    </span>
  );
}

export function FullPageSpinner({ label }: { label: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center text-slate-600 dark:text-slate-300">
      <Spinner label={label} />
    </div>
  );
}

/** Grey placeholder block shown while content loads. */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-md bg-slate-200 dark:bg-slate-800 ${className}`}
    />
  );
}
