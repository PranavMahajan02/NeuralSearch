import { ListFilter } from "lucide-react";

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

/** Type chips + platform dropdown. Changing either re-runs the search on the server. */
export function FilterBar({ type, platform, onTypeChange, onPlatformChange }: FilterBarProps) {
  return (
    <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-2">
      <ListFilter aria-hidden="true" className="h-3.5 w-3.5 text-slate-500" />
      <fieldset className="flex flex-wrap gap-1.5">
        <legend className="sr-only">File type</legend>
        {TYPES.map((value) => (
          <label
            key={value}
            className={`cursor-pointer select-none rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors duration-150 has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-blue-600 ${
              type === value
                ? "border-blue-600 bg-blue-600 text-white"
                : "border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:text-white"
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
      <label className="ml-auto flex items-center gap-2 text-xs font-semibold text-slate-600 dark:text-slate-400">
        Platform
        <select
          value={platform}
          onChange={(event) => onPlatformChange(event.target.value as SearchPlatform)}
          className="cursor-pointer rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
        >
          {PLATFORMS.map((value) => (
            <option key={value} value={value}>
              {value === "all" ? "All Channels" : PLATFORM_LABEL[value]}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
