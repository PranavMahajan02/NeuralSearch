import { useCallback, useState } from "react";

import { ApiError } from "../api/client";
import * as api from "../api/endpoints";
import type { SearchResult } from "../api/types";
import { useToast } from "../components/common/Toast";

type Openable = Pick<SearchResult, "platform" | "source_id" | "file">;

/**
 * Open a result: cloud files open their web page in a new tab (noopener);
 * local files are downloaded with the user's token as a blob and saved under
 * their real file name. Errors are shown as a toast.
 */
export function useOpenFile() {
  const { notify } = useToast();
  const [busyId, setBusyId] = useState<string | null>(null);

  const open = useCallback(
    async (item: Openable) => {
      setBusyId(item.source_id);

      try {
        const target = await api.openTarget(item);

        if (target.type === "url") {
          window.open(target.url, "_blank", "noopener,noreferrer");
          return;
        }

        const { blob, filename } = await api.downloadFile(target.url);
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = filename || target.filename || item.file || "download";
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000);
        notify(`Downloading ${link.download}`, "success");
      } catch (error) {
        notify(error instanceof ApiError ? error.message : "Could not open the file.", "error");
      } finally {
        setBusyId(null);
      }
    },
    [notify],
  );

  return { open, busyId };
}
