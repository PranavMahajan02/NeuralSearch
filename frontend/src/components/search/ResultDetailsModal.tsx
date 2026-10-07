import type { SearchResult } from "../../api/types";
import { formatBytes, formatDateTime, relevance } from "../../lib/format";
import { REASON_LABEL, platformLabel } from "../../lib/platforms";
import { Modal } from "../common/Modal";
import { Highlighted } from "./Highlighted";

interface Props {
  result: SearchResult;
  opening: boolean;
  onOpen: (result: SearchResult) => void;
  onClose: () => void;
}

const BUTTON = "cursor-pointer rounded-xl px-4 py-2 text-xs font-semibold transition-all";

export function ResultDetailsModal({ result, opening, onOpen, onClose }: Props) {
  const { percent } = relevance(result.score);
  const rows: [string, string][] = [
    ["Source Platform", platformLabel(result.platform)],
    ["Content Type", `${result.type}${result.extension ? ` (.${result.extension})` : ""}`],
    ["File Size", formatBytes(result.file_size)],
    ["Last Modified", formatDateTime(result.modified_at)],
    ["Relevance", `${percent}%`],
    ["Matched On", result.match.reasons.map((r) => REASON_LABEL[r] ?? r).join(", ") || "—"],
  ];

  if (result.repo) rows.splice(1, 0, ["Repository", `${result.owner}/${result.repo}`]);

  return (
    <Modal
      title={result.file}
      size="lg"
      onClose={onClose}
      footer={
        <>
          <button
            type="button"
            onClick={onClose}
            className={`${BUTTON} border border-slate-200 text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-800`}
          >
            Close
          </button>
          <button
            type="button"
            disabled={opening}
            onClick={() => onOpen(result)}
            className={`${BUTTON} bg-blue-600 text-white shadow-sm hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-700`}
          >
            {result.platform === "local" ? "Download" : "Open"}
          </button>
        </>
      }
    >
      <p className="mb-4 break-all font-mono text-[10px] text-slate-500 dark:text-slate-400">
        {result.display_path}
      </p>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-12">
        <section className="md:col-span-5">
          <h3 className="mb-3 font-mono text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            File Specifications
          </h3>
          <dl className="space-y-2 text-xs">
            {rows.map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between gap-4 border-b border-slate-100 py-1.5 dark:border-slate-800"
              >
                <dt className="text-slate-500 dark:text-slate-400">{label}</dt>
                <dd className="break-all text-right font-semibold text-slate-700 dark:text-slate-300">
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </section>
        <section className="flex flex-col md:col-span-7">
          <h3 className="mb-2 font-mono text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Matching Passage
          </h3>
          <div className="max-h-56 min-h-[11rem] flex-1 select-text overflow-y-auto whitespace-pre-wrap rounded-xl border border-slate-200 bg-slate-50 p-4 font-mono text-[11px] leading-relaxed text-slate-700 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300">
            {result.match.snippet && result.match.field !== "filename" ? (
              <Highlighted text={result.match.snippet} ranges={result.match.highlights} />
            ) : (
              <span className="text-slate-500 dark:text-slate-400">
                {result.match.reasons.includes("filename")
                  ? "Matched on the file name; no text passage to show."
                  : "Matched on what the image or video looks like; no text passage to show."}
              </span>
            )}
          </div>
        </section>
      </div>
    </Modal>
  );
}
