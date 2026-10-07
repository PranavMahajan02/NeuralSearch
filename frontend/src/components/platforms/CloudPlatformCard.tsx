import { useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

import type { CloudPlatform } from "../../api/endpoints";
import type { JobWithHistory, PlatformDetail } from "../../api/types";
import { isActiveJob } from "../../api/types";
import { usePlatformActions } from "../../hooks/usePlatformActions";
import { formatDateTime, formatRelative } from "../../lib/format";
import { PLATFORM_ICON, platformLabel } from "../../lib/platforms";
import { Button } from "../common/Button";
import { ConfirmDialog } from "../common/ConfirmDialog";
import { Skeleton } from "../common/Spinner";

interface CloudPlatformCardProps {
  platform: CloudPlatform;
  connected: boolean | undefined;
  account: string | null | undefined;
  detail: PlatformDetail | undefined;
  job: JobWithHistory | undefined;
  statusError?: string;
}

/** A failed job whose message asks the user to reconnect (expired token, missing scope). */
export function reconnectReason(
  connected: boolean | undefined,
  job: JobWithHistory | undefined,
): string | null {
  if (connected || !job || job.status !== "failed" || !job.error_message) return null;
  return /reconnect|expired|permission/i.test(job.error_message) ? job.error_message : null;
}

export function CloudPlatformCard({
  platform,
  connected,
  account,
  detail,
  job,
  statusError,
}: CloudPlatformCardProps) {
  const { connect, disconnect, startIndexing } = usePlatformActions();
  const [confirming, setConfirming] = useState(false);
  const Icon = PLATFORM_ICON[platform];
  const label = platformLabel(platform);
  const reconnect = reconnectReason(connected, job);
  const indexing = job ? isActiveJob(job) : false;

  return (
    <section
      aria-labelledby={`${platform}-title`}
      className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex items-center gap-3">
        <Icon aria-hidden="true" className="h-6 w-6" />
        <h2 id={`${platform}-title`} className="flex-1 text-base font-semibold">
          {label}
        </h2>
        {connected === undefined ? (
          <Skeleton className="h-5 w-20" />
        ) : (
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
              connected
                ? "bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200"
                : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
            }`}
          >
            {connected ? "Connected" : "Not connected"}
          </span>
        )}
      </div>

      {statusError && (
        <p className="text-sm text-rose-700 dark:text-rose-300">Status unavailable: {statusError}</p>
      )}

      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-slate-600 dark:text-slate-400">Account</dt>
        <dd className="truncate">{connected && account ? account : "—"}</dd>
        <dt className="text-slate-600 dark:text-slate-400">Indexed files</dt>
        <dd>{detail?.indexed_files ?? 0}</dd>
        <dt className="text-slate-600 dark:text-slate-400">Last indexed</dt>
        <dd title={formatDateTime(detail?.last_indexed_at)}>
          {detail?.last_indexed_at ? formatRelative(detail.last_indexed_at) : "Never"}
        </dd>
      </dl>

      {reconnect && (
        <div
          role="alert"
          className="flex gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-950 dark:bg-amber-950 dark:text-amber-100"
        >
          <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{reconnect}</p>
        </div>
      )}

      <div className="mt-auto flex flex-wrap gap-2">
        {connected ? (
          <>
            <Button
              variant="primary"
              disabled={indexing || startIndexing.isPending}
              onClick={() => startIndexing.mutate({ priority: platform, platforms: [platform] })}
            >
              <RefreshCw aria-hidden="true" className="h-4 w-4" />
              {indexing ? "Indexing…" : "Re-index"}
            </Button>
            <Button onClick={() => setConfirming(true)}>Disconnect</Button>
          </>
        ) : (
          <Button
            variant="primary"
            disabled={connect.isPending || connected === undefined}
            onClick={() => connect.mutate(platform)}
          >
            {reconnect ? "Reconnect" : `Connect ${label}`}
          </Button>
        )}
      </div>

      {confirming && (
        <ConfirmDialog
          title={`Disconnect ${label}?`}
          confirmLabel="Disconnect"
          danger
          busy={disconnect.isPending}
          option={`Also remove the ${detail?.indexed_files ?? 0} indexed ${label} files from search`}
          onCancel={() => setConfirming(false)}
          onConfirm={(purge) =>
            disconnect.mutate({ platform, purge }, { onSettled: () => setConfirming(false) })
          }
        >
          <p>
            CogniSeek revokes its access to your {label} account. Files already indexed stay searchable unless
            you remove them.
          </p>
        </ConfirmDialog>
      )}
    </section>
  );
}
