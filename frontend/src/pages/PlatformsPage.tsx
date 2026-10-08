import { useConnectionCount, useDriveStatus, useGithubStatus, useJobs, useStats } from "../api/queries";
import { CloudPlatformCard } from "../components/platforms/CloudPlatformCard";
import { LocalFoldersCard } from "../components/platforms/LocalFoldersCard";

export function PlatformsPage() {
  const stats = useStats();
  const jobs = useJobs();
  const drive = useDriveStatus();
  const github = useGithubStatus();
  const { connected, supported } = useConnectionCount();

  const detail = stats.data?.platforms;
  const jobOf = (platform: string) => jobs.data?.find((job) => job.platform === platform);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="mb-2 font-display text-lg font-bold text-slate-800 dark:text-slate-100">
        Unified Platforms Integration
      </h2>
      <p className="text-xs text-slate-600 dark:text-slate-400">
        {connected} of {supported} platforms connected. Manage connections, re-index, or link local folders.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <CloudPlatformCard
          platform="google_drive"
          connected={drive.data?.connected}
          account={drive.data?.account_email}
          detail={detail?.google_drive}
          job={jobOf("google_drive")}
          statusError={drive.isError ? drive.error.message : undefined}
        />
        <CloudPlatformCard
          platform="github"
          connected={github.data?.connected}
          account={github.data?.account_name}
          detail={detail?.github}
          job={jobOf("github")}
          statusError={github.isError ? github.error.message : undefined}
        />
        <div className="md:col-span-2">
          <LocalFoldersCard detail={detail?.local} job={jobOf("local")} />
        </div>
      </div>
    </div>
  );
}
