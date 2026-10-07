import type { SearchPlatform, SearchType } from "../../api/types";
import { PLATFORM_LABEL, TYPE_LABEL } from "../../lib/platforms";

const TYPES: SearchType[] = ["all", "document", "image", "audio", "video"];
const PLATFORMS: SearchPlatform[] = ["all", "local", "google_drive", "github"];

interface FilterBarProps {
  type: SearchType;
  platform: SearchPlatform;
  onTypeChange: (type: SearchType) => void;
  onPlatformChange: (platform: SearchPlatform) => void;
}

/** Type chips + platform select. Changing either re-runs the search on the server. */
export function FilterBar({ type, platform, onTypeChange, onPlatformChange }: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <fieldset className="flex flex-wrap gap-1.5">
        <legend className="sr-only">File type</legend>
        {TYPES.map((value) => (
          <label
            key={value}
            className={`cursor-pointer rounded-full px-3 py-1 text-sm font-medium ring-1 ring-inset has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-blue-600 ${
              type === value
                ? "bg-blue-700 text-white ring-blue-700"
                : "bg-white text-slate-700 ring-slate-300 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-200 dark:ring-slate-700"
            }`}
          >
            <input
              type="radio"
              name="search-type"
              value={value}
              checked={type === value}
              onChange={() => onTypeChange(value)}
              className="sr-only"
            />
            {TYPE_LABEL[value]}
          </label>
        ))}
      </fieldset>
      <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
        Platform
        <select
          value={platform}
          onChange={(event) => onPlatformChange(event.target.value as SearchPlatform)}
          className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
        >
          {PLATFORMS.map((value) => (
            <option key={value} value={value}>
              {value === "all" ? "All platforms" : PLATFORM_LABEL[value]}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
