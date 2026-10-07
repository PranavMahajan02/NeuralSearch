import { useJobs } from "../api/queries";
import { PLATFORMS } from "../api/types";
import { JobCard } from "../components/indexing/JobCard";
import { Skeleton } from "../components/common/Spinner";

export function IndexingPage() {
  const jobs = useJobs();

  if (jobs.isPending) {
    return (
      <div className="space-y-4" aria-busy="true">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (jobs.isError) {
    return (
      <p role="alert" className="text-sm text-rose-700 dark:text-rose-300">
        Could not load indexing jobs: {jobs.error.message}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Live status of the indexing jobs (refreshed every 2 seconds while one is running). Start a job from
        the Platforms page.
      </p>
      {PLATFORMS.map((platform) => (
        <JobCard
          key={platform}
          platform={platform}
          job={jobs.data.find((job) => job.platform === platform)}
        />
      ))}
    </div>
  );
}
