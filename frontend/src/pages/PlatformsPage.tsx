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
    <div className="space-y-6">
      <p className="text-sm text-slate-600 dark:text-slate-300">
        {connected} of {supported} platforms connected. Connect a platform, then index it to make its files
        searchable.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
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
      </div>
      <LocalFoldersCard detail={detail?.local} job={jobOf("local")} />
    </div>
  );
}
