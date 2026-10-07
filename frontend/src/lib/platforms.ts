import { Cloud, FileText, FolderOpen, Github, Image, Music, Video, type LucideIcon } from "lucide-react";

import type { PlatformName } from "../api/types";

export const PLATFORM_LABEL: Record<string, string> = {
  local: "Local storage",
  google_drive: "Google Drive",
  github: "GitHub",
};

export const PLATFORM_ICON: Record<string, LucideIcon> = {
  local: FolderOpen,
  google_drive: Cloud,
  github: Github,
};

export const PLATFORM_BADGE: Record<string, string> = {
  local:
    "bg-indigo-50 text-indigo-800 ring-indigo-200 dark:bg-indigo-950 dark:text-indigo-200 dark:ring-indigo-800",
  google_drive: "bg-sky-50 text-sky-800 ring-sky-200 dark:bg-sky-950 dark:text-sky-200 dark:ring-sky-800",
  github:
    "bg-slate-100 text-slate-800 ring-slate-300 dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-600",
};

export const TYPE_ICON: Record<string, LucideIcon> = {
  document: FileText,
  image: Image,
  audio: Music,
  video: Video,
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

/** Why a result matched, as returned by the API (match.reasons). */
export const REASON_LABEL: Record<string, string> = {
  filename: "File name",
  content: "Text",
  ocr: "Text in image",
  transcript: "Transcript",
  visual: "Looks similar",
  semantic: "Meaning",
};
