import React, { useState } from "react";
import { motion } from "motion/react";
import { Platform, PlatformId } from "../types";
import {
  HardDrive,
  Image,
  Github,
  Database,
  ChevronRight,
  Sparkles,
  Zap,
  ArrowRight,
  Sun,
  Moon
} from "lucide-react";

interface PageChooseFirstProps {
  platforms: Platform[];
  onStartIndexing: (priorityId: PlatformId) => void;
  onBack: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

export default function PageChooseFirst({ platforms, onStartIndexing, onBack, theme, onToggleTheme }: PageChooseFirstProps) {
  const connectedPlatforms = platforms.filter((p) => p.connected);
  const [selectedId, setSelectedId] = useState<PlatformId | null>(
    connectedPlatforms.length > 0 ? connectedPlatforms[0].id : null
  );

  const renderPlatformIcon = (iconName: string, color: string, active: boolean) => {
    const sizeClasses = `w-5 h-5 ${active ? "text-blue-600" : color}`;
    switch (iconName) {
      case "drive":
        return <HardDrive className={sizeClasses} />;
      case "photos":
        return <Image className={sizeClasses} />;
      case "github":
        return <Github className={sizeClasses} />;
      case "local":
        return <Database className={sizeClasses} />;
      default:
        return <HardDrive className={sizeClasses} />;
    }
  };

  const handleStart = () => {
    if (selectedId) {
      onStartIndexing(selectedId);
    }
  };

  const getQueuedPlatformsCount = () => {
    if (!selectedId) return 0;
    return connectedPlatforms.filter((p) => p.id !== selectedId).length;
  };

  return (
    <div id="choose_first_portal_wrapper" className="w-full min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col justify-between py-12 px-4 sm:px-6 md:px-8 transition-colors duration-200 relative">
      {/* Absolute top-right Theme Switcher */}
      <div className="absolute top-4 right-4 z-50">
        <button
          id="theme_toggle_choose_first"
          onClick={onToggleTheme}
          className="p-2.5 rounded-xl border border-slate-200/60 dark:border-slate-800/80 bg-white/75 dark:bg-slate-900/75 backdrop-blur-md text-slate-600 dark:text-slate-350 hover:text-slate-900 dark:hover:text-white shadow-xs cursor-pointer active:scale-95 transition-all"
          title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {theme === "dark" ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4 text-slate-600" />}
        </button>
      </div>

      {/* Header Info */}
      <div className="max-w-3xl mx-auto w-full text-center mt-6">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 rounded-full text-xs font-semibold uppercase tracking-wider mb-4 border border-amber-100 dark:border-amber-900/50"
        >
          <Zap className="w-3.5 h-3.5" />
          Step 3 of 4 • Choose Instant Portal
        </motion.div>

        <h2 id="choose_first_title" className="font-display text-3xl sm:text-4xl font-bold text-slate-800 dark:text-white tracking-tight">
          Choose a Platform to Start Searching
        </h2>

        <div className="mt-4 p-4 bg-blue-50/50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/40 rounded-xl max-w-xl mx-auto text-center">
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
            ⚡ Quick Onboarding Architecture
          </p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
            Index one platform first for faster access. The moment this first platform completes, full search unlocks! Other connected platforms will index in the background one-by-one.
          </p>
        </div>
      </div>

      {/* Connected Platforms Selection Selector List */}
      <div className="max-w-xl mx-auto w-full mt-10">
        <label className="block text-xs font-bold font-mono uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-3 ml-1">
          Your Connected Portals ({connectedPlatforms.length})
        </label>

        <div className="space-y-2.5">
          {connectedPlatforms.map((platform) => {
            const isSelected = selectedId === platform.id;
            return (
              <motion.div
                key={platform.id}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                id={`choose_card_${platform.id}`}
                onClick={() => setSelectedId(platform.id)}
                className={`py-4 px-5 rounded-xl border flex items-center justify-between cursor-pointer transition-all duration-200 ${isSelected
                  ? "bg-white dark:bg-slate-900 border-blue-500 dark:border-blue-500 ring-4 ring-blue-500/10 shadow-xs"
                  : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700 shadow-none"
                  }`}
              >
                <div className="flex items-center gap-4">
                  <div className={`p-2.5 rounded-lg border ${isSelected
                    ? "bg-blue-50/80 dark:bg-blue-950/40 border-blue-100 dark:border-blue-900/50"
                    : "bg-slate-50 dark:bg-slate-950 border-slate-150 dark:border-slate-850"
                    }`}>
                    {renderPlatformIcon(platform.iconName, platform.color, isSelected)}
                  </div>
                  <div>
                    <h3 className={`font-display font-semibold text-sm ${isSelected ? "text-blue-700 dark:text-blue-400" : "text-slate-800 dark:text-slate-100"
                      }`}>
                      {platform.name}
                    </h3>
                    <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
                      {isSelected ? "⭐️ Selected as prioritary source" : "Will index in the background"}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {isSelected ? (
                    <span className="text-[11px] font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 border border-blue-100 dark:border-blue-900/50 px-3 py-1 rounded-full uppercase tracking-wider">
                      Index First
                    </span>
                  ) : (
                    <span className="text-[11px] text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-800 border border-slate-150 dark:border-slate-750 px-3 py-1 rounded-full uppercase tracking-wider">
                      Queue Next
                    </span>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Informational flow preview */}
        {selectedId && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-6 p-4 bg-slate-100/60 dark:bg-slate-800/20 border border-slate-200/50 dark:border-slate-800/80 rounded-xl"
          >
            <h4 className="text-xs font-bold text-slate-700 dark:text-slate-400 uppercase tracking-wider font-mono">
              Pipeline Flow Visualizer
            </h4>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span className="bg-blue-600 text-white px-2.5 py-1 rounded-md font-semibold flex items-center gap-1 shadow-xs">
                1. Index {platforms.find((p) => p.id === selectedId)?.name}
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span className="bg-emerald-600 text-white px-2.5 py-1 rounded-md font-semibold shadow-xs">
                2. Unlock Search
              </span>
              {getQueuedPlatformsCount() > 0 && (
                <>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-2.5 py-1 rounded-md font-semibold">
                    3. Background Queue ({getQueuedPlatformsCount()} Platform{getQueuedPlatformsCount() === 1 ? "" : "s"})
                  </span>
                </>
              )}
            </div>
          </motion.div>
        )}
      </div>

      {/* Button controls */}
      <div className="max-w-xl mx-auto w-full mt-10 mb-6 flex items-center justify-between gap-4">
        <button
          onClick={onBack}
          className="px-5 py-3 hover:bg-slate-100 dark:hover:bg-slate-850 border border-slate-200/80 dark:border-slate-800/80 rounded-xl text-xs font-semibold cursor-pointer text-slate-600 dark:text-slate-400 transition-colors"
        >
          Back to Connections
        </button>

        <button
          id="btn_start_indexing_portal"
          disabled={!selectedId}
          onClick={handleStart}
          className={`flex-1 py-3.5 px-6 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 shadow-md transition-all duration-300 cursor-pointer ${selectedId
            ? "bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-500 text-white shadow-blue-100 dark:shadow-none active:translate-y-[1px]"
            : "bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-600 cursor-not-allowed shadow-none"
            }`}
        >
          <span>Start Indexing</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
