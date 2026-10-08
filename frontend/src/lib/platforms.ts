import { Database, FileText, Github, HardDrive, Image, Music, Play, type LucideIcon } from "lucide-react";

import type { PlatformName } from "../api/types";

export const PLATFORM_LABEL: Record<string, string> = {
  local: "Local Storage",
  google_drive: "Google Drive",
  github: "GitHub",
};

// Original CogniSeek platform marks.
export const PLATFORM_ICON: Record<string, LucideIcon> = {
  local: Database,
  google_drive: HardDrive,
  github: Github,
};

export const PLATFORM_COLOR: Record<string, string> = {
  local: "text-indigo-500 dark:text-indigo-400",
  google_drive: "text-blue-500 dark:text-blue-400",
  github: "text-slate-800 dark:text-slate-200",
};

export const PLATFORM_BADGE: Record<string, string> = {
  local: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  google_drive: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  github: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
};

export const TYPE_ICON: Record<string, LucideIcon> = {
  document: FileText,
  image: Image,
  audio: Music,
  video: Play,
};

export const TYPE_COLOR: Record<string, string> = {
  document: "text-blue-500",
  image: "text-emerald-500",
  audio: "text-amber-500",
  video: "text-purple-500",
};

export const TYPE_LABEL: Record<string, string> = {
  all: "All types",
  document: "Documents",
  image: "Images",
  audio: "Audio",
  video: "Video",
};

export function platformLabel(platform: PlatformName | string): string {
  return PLATFORM_LABEL[platform] ?? platform;
}

/** "1:05" / "1:02:05" from seconds. */
export function formatTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const ss = String(s).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}

/** The label of one match reason; a video's visual match names the frame. */
export function reasonLabel(reason: string, frameTimeS?: number | null): string {
  if (reason === "visual" && frameTimeS != null)
    return `Looks similar (frame at ${formatTimestamp(frameTimeS)})`;
  return REASON_LABEL[reason] ?? reason;
}

/** Why a result matched, as returned by the API (match.reasons). */
export const REASON_LABEL: Record<string, string> = {
  filename: "File name",
  content: "Text",
  ocr: "Text in image",
  transcript: "Transcript",
  visual: "Looks similar",
  semantic: "Meaning",
};
