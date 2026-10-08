import { useState } from "react";
import { motion } from "motion/react";
import { ArrowRight, ChevronRight, Zap } from "lucide-react";

import type { PlatformName } from "../../api/types";
import { platformLabel } from "../../lib/platforms";
import { PlatformLogo } from "../common/Badges";
import { OnboardingFrame } from "./OnboardingFrame";

interface Props {
  connected: PlatformName[];
  starting: boolean;
  onStart: (priority: PlatformName) => void;
  onBack: () => void;
  onSkip: () => void;
  skipping: boolean;
}

/** Step 2: pick ONE connected platform to index first; the others queue behind it. */
export function ChooseStep({ connected, starting, onStart, onBack, onSkip, skipping }: Props) {
  const [selected, setSelected] = useState<PlatformName | null>(connected.length === 1 ? connected[0] : null);
  const queued = selected ? connected.filter((p) => p !== selected).length : 0;

  return (
    <OnboardingFrame
      step={2}
      stepLabel="Choose Your Priority"
      icon={Zap}
      tone="amber"
      title="Choose your priority platform"
      intro={
        <div className="mx-auto mt-4 max-w-xl rounded-xl border border-blue-100 bg-blue-50/50 p-4 dark:border-blue-900/40 dark:bg-blue-950/20">
          <p className="text-sm font-medium text-slate-800 dark:text-slate-200">⚡ Index this first</p>
          <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
            Indexed first so you can start searching it right away; the others index in the background.
          </p>
        </div>
      }
      onSkip={onSkip}
      skipping={skipping}
    >
      <fieldset className="mx-auto mt-10 w-full max-w-xl">
        <legend className="mb-3 ml-1 font-mono text-xs font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
          Your connected platforms ({connected.length})
        </legend>
        <div className="space-y-2.5">
          {connected.map((platform) => {
            const isSelected = selected === platform;
            return (
              <motion.label
                key={platform}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                className={`flex cursor-pointer items-center justify-between rounded-xl border bg-white px-5 py-4 transition-all duration-200 has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-blue-600 dark:bg-slate-900 ${
                  isSelected
                    ? "border-blue-500 shadow-xs ring-4 ring-blue-500/10"
                    : "border-slate-200 hover:border-slate-300 dark:border-slate-800/80 dark:hover:border-slate-700"
                }`}
              >
                <input
                  type="radio"
                  name="priority-platform"
                  value={platform}
                  checked={isSelected}
                  onChange={() => setSelected(platform)}
                  className="sr-only"
                />
                <span className="flex items-center gap-4">
                  <span
                    className={`rounded-lg border p-2.5 ${isSelected ? "border-blue-100 bg-blue-50/80 dark:border-blue-900/50 dark:bg-blue-950/40" : "border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950"}`}
                  >
                    <PlatformLogo platform={platform} className="h-6 w-6" />
                  </span>
                  <span>
                    <span
                      className={`block font-display text-sm font-semibold ${isSelected ? "text-blue-700 dark:text-blue-400" : "text-slate-800 dark:text-slate-100"}`}
                    >
                      {platformLabel(platform)}
                    </span>
                    <span className="mt-0.5 block text-[11px] text-slate-600 dark:text-slate-400">
                      {isSelected ? "⭐ Indexed first" : "Will index in the background"}
                    </span>
                  </span>
                </span>
                <span
                  className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wider ${isSelected ? "border-blue-100 bg-blue-50 text-blue-700 dark:border-blue-900/50 dark:bg-blue-950/40 dark:text-blue-300" : "border-slate-200 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400"}`}
                >
                  {isSelected ? "Index this first" : "Queue next"}
                </span>
              </motion.label>
            );
          })}
        </div>

        {selected && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-6 rounded-xl border border-slate-200/50 bg-slate-100/60 p-4 dark:border-slate-800/80 dark:bg-slate-800/20"
          >
            <h2 className="font-mono text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-400">
              What happens next
            </h2>
            <ol className="mt-3 flex flex-wrap items-center gap-2 text-xs">
              <li className="rounded-md bg-blue-600 px-2.5 py-1 font-semibold text-white">
                1. Index {platformLabel(selected)}
              </li>
              <ChevronRight aria-hidden="true" className="h-3.5 w-3.5 text-slate-500" />
              <li className="rounded-md bg-emerald-700 px-2.5 py-1 font-semibold text-white">
                2. Search it right away
              </li>
              {queued > 0 && (
                <>
                  <ChevronRight aria-hidden="true" className="h-3.5 w-3.5 text-slate-500" />
                  <li className="rounded-md bg-slate-200 px-2.5 py-1 font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    3. Background queue ({queued} platform{queued === 1 ? "" : "s"})
                  </li>
                </>
              )}
            </ol>
          </motion.div>
        )}
      </fieldset>

      <div className="mx-auto mt-10 flex w-full max-w-xl items-center justify-between gap-4">
        <button
          type="button"
          onClick={onBack}
          className="cursor-pointer rounded-xl border border-slate-200/80 px-5 py-3 text-xs font-semibold text-slate-700 transition-colors hover:bg-slate-100 dark:border-slate-800/80 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          Back to Connections
        </button>
        <button
          type="button"
          disabled={!selected || starting}
          onClick={() => selected && onStart(selected)}
          className="flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-3.5 text-sm font-semibold text-white shadow-md shadow-blue-100 transition-all duration-300 hover:bg-blue-700 active:translate-y-[1px] disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-700 disabled:shadow-none dark:shadow-none dark:disabled:bg-slate-800 dark:disabled:text-slate-300"
        >
          {starting ? "Starting…" : "Start indexing"}
          <ArrowRight aria-hidden="true" className="h-4 w-4" />
        </button>
      </div>
    </OnboardingFrame>
  );
}
