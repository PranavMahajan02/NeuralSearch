import type { Job } from "../../api/types";
import { formatDateTime, formatDuration } from "../../lib/format";
import { JobStatusBadge } from "../common/Badges";

const TH = "py-1 pr-3 font-medium";

/** The collapsible "Last N runs" table of one platform. */
export function JobHistory({ jobs }: { jobs: Job[] }) {
  if (jobs.length === 0) return null;

  return (
    <details className="text-xs">
      <summary className="cursor-pointer font-semibold text-slate-700 dark:text-slate-300">
        {jobs.length === 1 ? "Last run" : `Last ${jobs.length} runs`}
      </summary>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-left text-xs">
          <caption className="sr-only">Recent runs</caption>
          <thead className="font-mono text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <tr>
              <th scope="col" className={TH}>
                Started
              </th>
              <th scope="col" className={TH}>
                Status
              </th>
              <th scope="col" className={TH}>
                Indexed
              </th>
              <th scope="col" className={TH}>
                Failed
              </th>
              <th scope="col" className={TH}>
                Skipped
              </th>
              <th scope="col" className="py-1 font-medium">
                Duration
              </th>
            </tr>
          </thead>
          <tbody className="text-slate-700 dark:text-slate-300">
            {jobs.map((job) => (
              <tr key={job.id} className="border-t border-slate-100 dark:border-slate-800">
                <td className="whitespace-nowrap py-1.5 pr-3">
                  {formatDateTime(job.started_at ?? job.created_at)}
                </td>
                <td className="py-1.5 pr-3">
                  <JobStatusBadge status={job.status} />
                </td>
                <td className="py-1.5 pr-3 font-mono">{job.succeeded_files}</td>
                <td className="py-1.5 pr-3 font-mono">{job.failed_files}</td>
                <td className="py-1.5 pr-3 font-mono">{job.skipped_files}</td>
                <td className="whitespace-nowrap py-1.5 font-mono">
                  {formatDuration(job.started_at, job.completed_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
