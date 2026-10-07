import type { SearchResult } from "../../api/types";
import { formatBytes, formatDateTime, relevance } from "../../lib/format";
import { REASON_LABEL } from "../../lib/platforms";
import { PlatformBadge } from "../common/Badges";
import { Button } from "../common/Button";
import { Modal } from "../common/Modal";
import { Highlighted } from "./Highlighted";

interface Props {
  result: SearchResult;
  opening: boolean;
  onOpen: (result: SearchResult) => void;
  onClose: () => void;
}

export function ResultDetailsModal({ result, opening, onOpen, onClose }: Props) {
  const { percent } = relevance(result.score);
  const rows: [string, string][] = [
    ["Location", result.display_path],
    ["Type", `${result.type}${result.extension ? ` (.${result.extension})` : ""}`],
    ["Size", formatBytes(result.file_size)],
    ["Modified", formatDateTime(result.modified_at)],
    ["Relevance", `${percent}%`],
    ["Matched on", result.match.reasons.map((r) => REASON_LABEL[r] ?? r).join(", ") || "—"],
  ];

  if (result.repo) rows.splice(1, 0, ["Repository", `${result.owner}/${result.repo}`]);

  return (
    <Modal
      title={result.file}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Close</Button>
          <Button variant="primary" disabled={opening} onClick={() => onOpen(result)}>
            {result.platform === "local" ? "Download" : "Open"}
          </Button>
        </>
      }
    >
      <div className="space-y-4 text-sm">
        <PlatformBadge platform={result.platform} />
        <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2">
          {rows.map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="font-medium text-slate-600 dark:text-slate-400">{label}</dt>
              <dd className="break-all">{value}</dd>
            </div>
          ))}
        </dl>
        {result.match.snippet && result.match.field !== "filename" && (
          <section>
            <h3 className="mb-1 font-medium text-slate-600 dark:text-slate-400">Matching passage</h3>
            <p className="rounded-lg bg-slate-50 p-3 leading-relaxed dark:bg-slate-800">
              <Highlighted text={result.match.snippet} ranges={result.match.highlights} />
            </p>
          </section>
        )}
      </div>
    </Modal>
  );
}
