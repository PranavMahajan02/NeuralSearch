import { apiBlob, apiJson } from "./http";

type OpenTarget =
  | { type: "url"; url: string }
  | { type: "download"; url: string; filename?: string };

/**
 * Open a search result in the browser. Nothing is opened on the server:
 * Drive / GitHub open in a new tab, local files are downloaded with auth.
 * Throws an Error carrying the backend's message on failure.
 */
export async function openFile(platform: string, path?: string, file_id?: string, source_id?: string) {
  // source_id identifies the indexed file (local path / Drive id / owner/repo:path);
  // the backend only opens sources this user has indexed.
  const target = await apiJson<OpenTarget>("/open/", {
    method: "POST",
    json: { platform, path, file_id, source_id },
    errorMessage: "Unable to open file.",
  });

  if (target.type === "url") {
    window.open(target.url, "_blank", "noopener");
    return target;
  }

  const { blob, filename } = await apiBlob(target.url, { errorMessage: "Unable to download file." });

  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename || target.filename || "download";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000);

  return target;
}
