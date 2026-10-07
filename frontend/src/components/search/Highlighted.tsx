import { highlightParts } from "../../lib/format";

/** Text with the API's highlight ranges wrapped in <mark> (React elements, no HTML strings). */
export function Highlighted({ text, ranges }: { text: string; ranges: number[][] }) {
  return (
    <>
      {highlightParts(text, ranges).map((part, index) =>
        part.mark ? (
          <mark key={index} className="rounded bg-amber-200 px-0.5 text-slate-900 dark:bg-amber-400/80">
            {part.text}
          </mark>
        ) : (
          <span key={index}>{part.text}</span>
        ),
      )}
    </>
  );
}
