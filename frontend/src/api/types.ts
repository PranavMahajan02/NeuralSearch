// Named aliases for the generated backend types (src/api/schema.d.ts,
// regenerate with `npm run gen:api`). Never edit the generated file by hand.
import type { components } from "./schema";

type Schemas = components["schemas"];

export type PlatformName = Schemas["PlatformName"];
export type SearchPlatform = Schemas["SearchPlatform"];
export type SearchType = Schemas["SearchType"];

export type SearchRequest = Schemas["SearchRequest"];
export type SearchResponse = Schemas["SearchResponse"];
export type SearchResult = Schemas["SearchResult"];
export type MatchInfo = Schemas["MatchInfo"];
export type Suggestion = Schemas["Suggestion"];
export type SuggestionsResponse = Schemas["SuggestionsResponse"];

export type DashboardStats = Schemas["DashboardStats"];
export type PlatformDetail = Schemas["PlatformDetail"];
export type RecentFile = Schemas["RecentFile"];
export type RecentResponse = Schemas["RecentResponse"];

export type Job = Schemas["Job"];
export type JobStatus = Job["status"];
export type JobWithHistory = Schemas["JobWithHistory"];
export type JobError = Schemas["JobError"];
export type JobErrorsResponse = Schemas["JobErrorsResponse"];
export type IndexQueuedResponse = Schemas["IndexQueuedResponse"];

export type FoldersResponse = Schemas["FoldersResponse"];
export type PickFolderResponse = Schemas["PickFolderResponse"];
export type DriveStatus = Schemas["DriveStatus"];
export type GithubStatus = Schemas["GithubStatus"];
export type ConnectResponse = Schemas["ConnectResponse"];
export type DisconnectResponse = Schemas["DisconnectResponse"];
export type OpenResponse = Schemas["OpenResponse"];
export type LoginStateResponse = Schemas["LoginStateResponse"];

export type User = Schemas["UserResponse"];
export type TokenResponse = Schemas["TokenResponse"];
export type RegisterRequest = Schemas["RegisterRequest"];

/** The platforms CogniSeek supports, in display order. */
export const PLATFORMS: readonly PlatformName[] = ["local", "google_drive", "github"];

export const ACTIVE_JOB_STATUSES: readonly JobStatus[] = ["queued", "running"];

export function isActiveJob(job: Pick<Job, "status">): boolean {
  return ACTIVE_JOB_STATUSES.includes(job.status);
}
