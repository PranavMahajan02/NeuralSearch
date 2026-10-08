import { useQuery } from "@tanstack/react-query";

import * as api from "../../api/endpoints";
import { keys } from "../../api/queries";
import { useAuth } from "../../auth/AuthContext";
import { Skeleton } from "../common/Spinner";

/** Per-file errors of one job (already sanitized by the backend: no URLs, secrets or foreign paths). */
export function JobErrors({ jobId }: { jobId: string }) {
  const { userId } = useAuth();
  const errors = useQuery({
    queryKey: keys.jobErrors(userId, jobId),
    queryFn: ({ signal }) => api.getJobErrors(jobId, signal),
  });

  if (errors.isPending) return <Skeleton className="h-12" />;

  if (errors.isError)
    return (
      <p className="text-sm text-rose-700 dark:text-rose-300">
        Could not load errors: {errors.error.message}
      </p>
    );

  if (errors.data.errors.length === 0)
    return <p className="text-sm text-slate-600 dark:text-slate-400">No file errors recorded.</p>;

  return (
    <ul className="max-h-64 space-y-2 overflow-y-auto text-sm">
      {errors.data.errors.map((error, index) => (
        <li key={`${error.file}-${index}`} className="rounded-md bg-rose-50 p-2 dark:bg-rose-950">
          <p className="break-all font-medium">{error.file}</p>
          <p className="text-rose-900 dark:text-rose-200">{error.error}</p>
        </li>
      ))}
    </ul>
  );
}
