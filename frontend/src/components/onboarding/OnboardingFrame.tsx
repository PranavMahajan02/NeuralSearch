import type { ReactNode } from "react";
import { motion } from "motion/react";
import type { LucideIcon } from "lucide-react";

import { ThemeToggle } from "../common/Brand";

interface Props {
  step: number;
  stepLabel: string;
  icon: LucideIcon;
  tone: "blue" | "amber";
  title: string;
  children: ReactNode;
  intro: ReactNode;
  onSkip: () => void;
  skipping: boolean;
}

const TONE = {
  blue: "bg-blue-50 text-blue-800 border-blue-100 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-900/50",
  amber:
    "bg-amber-50 text-amber-800 border-amber-100 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900/50",
};

/** The full-page frame shared by the onboarding steps (original CogniSeek onboarding look). */
export function OnboardingFrame({
  step,
  stepLabel,
  icon: Icon,
  tone,
  title,
  intro,
  children,
  onSkip,
  skipping,
}: Props) {
  return (
    <div className="relative flex min-h-screen w-full flex-col bg-slate-50 px-4 py-12 transition-colors duration-200 sm:px-6 md:px-8 dark:bg-slate-950">
      <div className="absolute right-4 top-4 z-50">
        <ThemeToggle floating />
      </div>

      <main className="flex flex-1 flex-col">
        <header className="mx-auto mt-6 w-full max-w-4xl text-center">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className={`mb-4 inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${TONE[tone]}`}
          >
            <Icon aria-hidden="true" className="h-3.5 w-3.5" />
            Step {step} of 2 • {stepLabel}
          </motion.div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-slate-800 sm:text-4xl dark:text-white">
            {title}
          </h1>
          <div className="mx-auto mt-2 max-w-lg text-sm text-slate-600 dark:text-slate-400">{intro}</div>
        </header>

        {children}

        <div className="mt-8 text-center">
          <button
            type="button"
            onClick={onSkip}
            disabled={skipping}
            className="text-xs font-semibold text-slate-600 underline-offset-2 hover:text-slate-900 hover:underline dark:text-slate-400 dark:hover:text-white"
          >
            Skip for now — go to the dashboard
          </button>
        </div>
      </main>
    </div>
  );
}
