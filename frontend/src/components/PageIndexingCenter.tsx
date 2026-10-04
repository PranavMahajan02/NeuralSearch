import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Platform, PlatformId, IndexLog, DashboardStats } from "../types";
import { MOCK_FILES } from "../data/mockFiles";
import { getDashboardStats } from "../services/dashboard";
import {
  startScheduler,
  getSchedulerStatus
} from "../services/scheduler";
import {
  Database,
  CheckCircle2,
  AlertCircle,
  HardDrive,
  Image,
  Github,
  FileText,
  Layers,
  FileCode,
  Clock,
  ArrowRight,
  Info,
  RefreshCw,
  Sun,
  Moon
} from "lucide-react";

interface PageIndexingCenterProps {
  isOnboarding: boolean;
  platforms: Platform[];
  onUpdatePlatforms: React.Dispatch<React.SetStateAction<Platform[]>>;
  indexedPlatforms: string[];
  onUpdateIndexedPlatforms: (indexed: string[]) => void;
  stats: DashboardStats;
  onUpdateStats: React.Dispatch<React.SetStateAction<DashboardStats>>;
  onEnterDashboard?: () => void;
  theme?: "light" | "dark";
  onToggleTheme?: () => void;
  streamFeed: IndexLog[];
  priorityPlatformId?: PlatformId | null;
  indexJobs: any[];
}

export default function PageIndexingCenter({
  isOnboarding,
  platforms,
  onUpdatePlatforms,
  indexedPlatforms,
  onUpdateIndexedPlatforms,
  stats,
  onUpdateStats,
  onEnterDashboard,
  theme = "light",
  onToggleTheme,
  streamFeed,
  priorityPlatformId,
  indexJobs
}: PageIndexingCenterProps) {
  const activePlatform = platforms.find(
    (p) =>
      p.connected &&
      (p.status === "indexing" || p.status === "paused")
  );

  const activePlatformId = activePlatform
    ? activePlatform.id
    : null;

  const activeJob = indexJobs.find((job: any) => {

    const backendPlatform =
      activePlatform?.id === "local_storage"
        ? "local"
        : activePlatform?.id;

    return (
      job.platform === backendPlatform &&
      job.status === "indexing"
    );

  });

  const handlePause = () => {
    if (!activePlatformId) return;
    onUpdatePlatforms((prev) =>
      prev.map((p) => (p.id === activePlatformId ? { ...p, status: "paused" as const } : p))
    );
  };

  const handleResume = () => {
    if (!activePlatformId) return;
    onUpdatePlatforms((prev) =>
      prev.map((p) => (p.id === activePlatformId ? { ...p, status: "indexing" as const } : p))
    );
  };

  const handleCancel = () => {
    if (!activePlatformId) return;
    onUpdatePlatforms((prev) =>
      prev.map((p) => {
        if (p.id === activePlatformId) {
          return { ...p, status: "idle" as const, progress: 0 };
        } else if (p.status === "waiting") {
          return { ...p, status: "idle" as const };
        }
        return p;
      })
    );
  };

  const renderPlatformLogo = (iconName: string, color: string, sizeClasses = "w-5 h-5") => {
    switch (iconName) {
      case "drive":
        return <HardDrive className={`${sizeClasses} ${color}`} />;
      case "photos":
        return <Image className={`${sizeClasses} ${color}`} />;
      case "github":
        return <Github className={`${sizeClasses} ${color}`} />;
      case "local":
        return <Database className={`${sizeClasses} ${color}`} />;
      default:
        return <HardDrive className={`${sizeClasses} ${color}`} />;
    }
  };

  // Compute platform variables
  const currentActivePlatform = platforms.find((p) => p.id === activePlatformId);
  const queuedPlatforms = platforms.filter((p) => p.connected && p.status === "waiting");
  const completedPlatforms = platforms.filter((p) => p.connected && p.status === "indexed");

  const priorityPlatform = platforms.find((p) => p.id === priorityPlatformId);
  const isPriorityCompleted = priorityPlatform ? priorityPlatform.status === "indexed" : false;

  return (
    <div id="index_center_wrapper" className={`w-full ${isOnboarding ? "min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col justify-between py-12 px-4 sm:px-6 md:px-8 transition-colors duration-200 relative" : "p-1 md:p-4"}`}>

      {/* Absolute top-right Theme Switcher */}
      {isOnboarding && (
        <div className="absolute top-4 right-4 z-50">
          <button
            id="theme_toggle_indexing"
            onClick={onToggleTheme}
            className="p-2.5 rounded-xl border border-slate-200/60 dark:border-slate-800/80 bg-white/75 dark:bg-slate-900/75 backdrop-blur-md text-slate-600 dark:text-slate-350 hover:text-slate-900 dark:hover:text-white shadow-xs cursor-pointer active:scale-95 transition-all"
            title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {theme === "dark" ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4 text-slate-600" />}
          </button>
        </div>
      )}

      {/* Onboarding Header */}
      {isOnboarding && (
        <div className="max-w-4xl mx-auto w-full text-center mt-4">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 rounded-full text-xs font-semibold uppercase tracking-wider mb-4 border border-emerald-100 dark:border-emerald-900/50">
            <RefreshCw className="w-3 h-3 animate-spin" />
            Step 4 of 4 • Primary Sync Active
          </div>

          <h2 id="index_center_title" className="font-display text-3xl sm:text-4xl font-bold text-slate-800 dark:text-white tracking-tight">
            Building Instant Search Index
          </h2>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-lg mx-auto">
            Please wait while we set up secure indexes over your priority source. Once this completes, the full dashboard unlocks immediately.
          </p>
        </div>
      )}

      {/* Main Grid View */}
      <div className={`w-full ${isOnboarding ? "max-w-4xl mx-auto mt-10" : "mt-2"} grid grid-cols-1 md:grid-cols-3 gap-6`}>

        {/* Left Side: Main Status Panel & Streaming Activity Feed */}
        <div className="md:col-span-2 space-y-6">

          {/* Main Ticking Indexer Progress Card */}
          <div id="main_indexing_card" className="bg-white border border-slate-200 shadow-xs rounded-2xl p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-display font-bold text-slate-800 text-lg flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-600" />
                Current Processing Platform
              </h3>

              {currentActivePlatform ? (
                <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase font-mono ${currentActivePlatform.status === "paused"
                  ? "bg-amber-50 text-amber-700 border border-amber-100"
                  : "bg-blue-50 text-blue-700 border border-blue-100 animate-pulse"
                  }`}>
                  {currentActivePlatform.status}
                </span>
              ) : (
                <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-500 border border-slate-200 text-[10px] font-bold tracking-wider uppercase font-mono">
                  IDLE
                </span>
              )}
            </div>

            {currentActivePlatform ? (
              <div id="active_indexer_progress_container" className="space-y-4">
                <div className="flex items-center gap-4 p-4 bg-slate-50 border border-slate-100 rounded-xl">
                  {renderPlatformLogo(currentActivePlatform.iconName, currentActivePlatform.color, "w-10 h-10")}
                  <div className="flex-1 min-w-0">
                    <h4 className="font-display font-bold text-slate-800 text-base">
                      {currentActivePlatform.name}
                    </h4>
                    <p className="text-xs text-slate-400 mt-0.5 truncate">
                      Scanning directories, compiling metadata, extracting contents...
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="font-display font-bold text-2xl text-blue-600 font-mono">
                      {
                        indexJobs.find(j =>

                          (j.platform === "local" && currentActivePlatform.id === "local_storage") ||

                          j.platform === currentActivePlatform.id

                        )?.progress ?? currentActivePlatform.progress
                      }%
                    </span>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-blue-600 rounded-full"
                    style={{
                      width: `${indexJobs.find(j =>

                        (j.platform === "local" && currentActivePlatform.id === "local_storage") ||

                        j.platform === currentActivePlatform.id

                      )?.progress ?? currentActivePlatform.progress
                        }%`
                    }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                  />
                </div>
                {(() => {

                  const job = indexJobs.find(j =>

                    (j.platform === "local" &&
                      currentActivePlatform.id === "local_storage") ||

                    j.platform === currentActivePlatform.id

                  );

                  if (!job) return null;

                  return (

                    <div className="mt-4 space-y-1">

                      <p className="text-sm font-medium text-slate-700">

                        {job.indexed_files} / {job.total_files} files indexed

                      </p>

                      <p className="text-xs text-slate-500 truncate">

                        Current File: {job.current_file || "Preparing..."}

                      </p>

                    </div>

                  );

                })()}

              </div>
            ) : (
              <div className="p-8 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
                <AlertCircle className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                <p className="text-sm font-semibold text-slate-600">Synchronization Complete</p>
                <p className="text-xs text-slate-400 max-w-xs mx-auto mt-1">
                  All connected platforms have been fully indexed and are ready for search operations.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Platform Status, Queue, Controls, Stats */}
        <div className="space-y-6">

          {/* Static Stats Panel (Indexing center specific counts) */}
          {!isOnboarding && (
            <div className="bg-slate-900 text-white rounded-2xl p-5 shadow-lg border border-slate-800">
              <h3 className="text-white text-xs font-bold uppercase tracking-widest font-mono mb-4 text-slate-400">
                CogniSeek Indexing Stats
              </h3>

              <div className="grid grid-cols-2 gap-x-4 gap-y-4">
                <div className="border-b border-slate-800 pb-3">
                  <span className="text-[10px] text-slate-400 block font-normal">Connected Portals</span>
                  <span className="font-display font-semibold text-xl text-white mt-1 block">
                    {stats.connectedPlatforms} / 4
                  </span>
                </div>
                <div className="border-b border-slate-800 pb-3">
                  <span className="text-[10px] text-slate-400 block font-normal">Indexed Files</span>
                  <span className="font-display font-semibold text-xl text-white mt-1 block">
                    {stats.indexedFiles}
                  </span>
                </div>
                <div className="border-b border-slate-800 pb-3">
                  <span className="text-[10px] text-slate-400 block font-normal">Images Cataloged</span>
                  <span className="font-display font-semibold text-xl text-emerald-400 mt-1 block">
                    {stats.indexedImages}
                  </span>
                </div>
                <div className="border-b border-slate-800 pb-3">
                  <span className="text-[10px] text-slate-400 block font-normal">Audio Files</span>
                  <span className="font-display font-semibold text-xl text-amber-400 mt-1 block">
                    {stats.indexedAudio}
                  </span>
                </div>
                <div className="border-b border-slate-800 pb-3">
                  <span className="text-[10px] text-slate-400 block font-normal">Videos Cataloged</span>
                  <span className="font-display font-semibold text-xl text-purple-400 mt-1 block">
                    {stats.indexedVideos}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block font-normal">Active Sync Portals</span>
                  <span className="font-display font-semibold text-sm text-blue-400 mt-1 block uppercase">
                    {stats.platformsReady} Platforms Ready
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block font-normal">Last Indexed Sync</span>
                  <span className="font-display font-semibold text-xs text-slate-350 mt-1 block font-mono">
                    {stats.lastSyncTime || "Waiting..."}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Platform Status List (Waiting / Completed queues) */}
          <div className="bg-white border border-slate-200 shadow-xs rounded-2xl p-6">
            <h3 className="font-display font-bold text-slate-800 text-sm mb-4">
              Platform Sync Roadmap
            </h3>

            <div className="space-y-3">
              {platforms.filter((p) => p.connected).map((p) => {
                const isActive = p.id === activePlatformId;
                return (
                  <div
                    key={p.id}
                    className={`flex items-center justify-between p-2.5 rounded-xl border ${isActive
                      ? "bg-blue-50/50 border-blue-200"
                      : "bg-slate-50 border-slate-100"
                      }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      {renderPlatformLogo(p.iconName, p.color, "w-4.5 h-4.5")}
                      <span className="text-xs font-semibold text-slate-800 truncate">
                        {p.name}
                      </span>
                    </div>

                    <div>
                      {p.status === "indexed" ? (
                        <span className="text-[10px] text-emerald-600 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider flex items-center gap-1">
                          ✓ Ready
                        </span>
                      ) : p.status === "indexing" ? (
                        <span className="text-[10px] text-blue-600 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider flex items-center gap-1 font-mono">
                          {p.progress}%
                        </span>
                      ) : p.status === "paused" ? (
                        <span className="text-[10px] text-amber-600 bg-amber-50 border border-amber-100 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">
                          Paused
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-500 bg-slate-100 border border-slate-150 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">
                          Queued
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

        </div>
      </div>

      {/* Onboarding Finish Footer Link bar */}
      {isOnboarding && (
        <div className="max-w-4xl mx-auto w-full mt-10 flex flex-col items-center gap-4 mb-4">
          {!isPriorityCompleted ? (
            <div className="flex items-center gap-2 p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-100 dark:border-amber-900/50 text-amber-800 dark:text-amber-200 rounded-xl max-w-sm text-center">
              <Info className="w-4 h-4 text-amber-600 shrink-0" />
              <p className="text-[11px] font-medium leading-relaxed">
                Background index of {priorityPlatform?.name || "Priority Platform"} is working. Once this first portal finishes, the search dashboard activates instantly!
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="flex flex-col items-center gap-2.5 p-5 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-150 dark:border-emerald-800/80 text-emerald-800 dark:text-emerald-200 rounded-2xl text-center shadow-xs max-w-2xl"
              >
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0 fill-emerald-100 dark:fill-emerald-950/30 font-bold" />
                  <span className="text-xs font-bold uppercase tracking-wide">
                    Priority Platform Indexed Successfully
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed font-normal mt-1">
                  Priority platform indexed successfully. You can start searching now while the remaining platforms continue indexing in the background.
                </p>
              </motion.div>

              <button
                id="btn_enter_saas_dashboard"
                onClick={onEnterDashboard}
                className="py-3.5 px-10 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-xl inline-flex items-center gap-2 shadow-md shadow-blue-100 cursor-pointer active:translate-y-[1px] transition-all"
              >
                <span>Go to Dashboard</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
