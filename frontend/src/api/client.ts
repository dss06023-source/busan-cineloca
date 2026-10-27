// ApiClient: OpenAPI에서 만든 타입(schema.d.ts)과 얇은 fetch 래퍼.
// 모든 요청에 X-Session-Id를, AI 요청(API-004·012·013)에는 X-Notice-Version을 붙인다.
import { messageFor } from "./errors";
import type { components } from "./schema";
import { sessionId } from "../lib/session";
import { KEYS, readJson } from "../lib/storage";

export type Schemas = components["schemas"];
export type MapItem = Schemas["MapItemOut"];
export type SearchIn = Schemas["SearchIn"];
export type SearchOut = Schemas["SearchOut"];
export type LocationDetail = Schemas["LocationDetailOut"];
export type Meta = Schemas["MetaOut"];
export type SourceCard = Schemas["SourceCardOut"];
export type SourcesOut = Schemas["SourcesOut"];
export type WorkList = Schemas["WorkListOut"];
export type WorkDetail = Schemas["WorkDetailOut"];
export type Rating = Schemas["RatingOut"];
export type Intro = Schemas["IntroOut"];
export type Spoiler = "none" | "partial";
export type QueryOut = Schemas["QueryOut"];
export type Criteria = Schemas["CriteriaIO"];
export type Chip = Schemas["ChipOut"];
export type CourseList = Schemas["CourseListOut"];
export type CourseDetail = Schemas["CourseDetailOut"];
export type RouteOut = Schemas["RouteOut"];
export type PlanIn = Schemas["PlanIn"];
export type StartIn = Schemas["StartIn"];
export type AICourseIn = Schemas["AICourseIn"];
export type AICourseOut = Schemas["AICourseOut"];
export type CertifyIn = Schemas["CertifyIn"];
export type CertifyOut = Schemas["CertifyOut"];
export type VerifyOut = Schemas["VerifyOut"];
export type BadgeIn = Schemas["BadgeIn"];
export type BadgeOut = Schemas["BadgeOut"];
export type SyncReport = Schemas["SyncReportOut"];
export type ReviewItem = Schemas["ReviewOut"];
export type LocationAttrsIn = Schemas["LocationAttrsIn"];
export type AdminLocation = Schemas["AdminLocationOut"];
export type AdminCourse = Schemas["AdminCourseOut"];
export type CourseDraftIn = Schemas["CourseDraftIn"];
export type CourseEditIn = Schemas["CourseEditIn"];
export type WorkListParams = { q?: string; genre?: string; sort?: "locations" | "year"; page?: number };

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string | undefined,
    public retryAfter: number | null = null,
    // 서버가 보낸 문구. 사용자 화면은 코드별 고정 문구만 쓰고, 관리자 화면만 이유를 보여 준다
    public serverMessage: string | null = null,
  ) {
    super(messageFor(code));
  }
}

// 403 ERR-002를 받으면 NoticeGate를 다시 띄우도록 알린다
export const NOTICE_REQUIRED_EVENT = "cl:notice-required";

type Options = { method?: string; body?: unknown; ai?: boolean; signal?: AbortSignal };

export async function api<T>(path: string, { method = "GET", body, ai = false, signal }: Options = {}): Promise<T> {
  const headers: Record<string, string> = { "X-Session-Id": sessionId() };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (ai) {
    const notice = readJson<string | null>(KEYS.notice, null);
    if (notice) headers["X-Notice-Version"] = notice;
  }
  let res: Response;
  try {
    res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, "ERR-015");
  }
  if (res.ok) return (res.status === 204 ? undefined : await res.json()) as T;
  let code: string | undefined;
  let retryAfter: number | null = null;
  let serverMessage: string | null = null;
  try {
    const err = (await res.json()).error;
    code = err?.code;
    retryAfter = err?.retry_after ?? null;
    serverMessage = typeof err?.message === "string" ? err.message : null;
  } catch {
    code = res.status >= 500 ? "ERR-016" : undefined;
  }
  if (code === "ERR-002") window.dispatchEvent(new Event(NOTICE_REQUIRED_EVENT));
  throw new ApiError(res.status, code, retryAfter, serverMessage);
}

export const endpoints = {
  searchLocations: (body: SearchIn) => api<SearchOut>("/api/locations/search", { method: "POST", body }),
  location: (id: number) => api<LocationDetail>(`/api/locations/${id}`),
  meta: () => api<Meta>("/api/meta"),
  sources: () => api<SourcesOut>("/api/sources"),
  works: (p: WorkListParams) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(p)) if (v !== undefined && v !== "") qs.set(k, String(v));
    return api<WorkList>(`/api/works?${qs}`);
  },
  work: (id: number) => api<WorkDetail>(`/api/works/${id}`),
  rating: (id: number) => api<Rating>(`/api/works/${id}/rating`),
  ask: (text: string, here?: { lat: number; lon: number } | null) =>
    api<QueryOut>("/api/query", { method: "POST", body: { text, here: here ?? null }, ai: true }),
  search: (criteria: Criteria, labels: Record<string, string> = {}) =>
    api<QueryOut>("/api/search", { method: "POST", body: { criteria, labels } }),
  resetQuery: () => api<void>("/api/query/session", { method: "DELETE" }),
  courses: (theme?: string) => api<CourseList>(`/api/courses${theme ? `?theme=${theme}` : ""}`),
  course: (id: number) => api<CourseDetail>(`/api/courses/${id}`),
  planCourse: (body: PlanIn) => api<RouteOut>("/api/courses/plan", { method: "POST", body }),
  aiCourse: (body: AICourseIn) => api<AICourseOut>("/api/courses/ai", { method: "POST", body, ai: true }),
  certify: (body: CertifyIn) => api<CertifyOut>("/api/stamps", { method: "POST", body }),
  verifyStamps: (tokens: string[], badges: string[]) =>
    api<VerifyOut>("/api/stamps/verify", { method: "POST", body: { tokens, badges } }),
  badge: (body: BadgeIn) => api<BadgeOut>("/api/badges", { method: "POST", body }),
  adminLogin: (password: string) => api<void>("/api/admin/session", { method: "POST", body: { password } }),
  adminLogout: () => api<void>("/api/admin/session", { method: "DELETE" }),
  syncReport: () => api<SyncReport>("/api/admin/sync?limit=10"),
  requestSync: () => api<{ run_id: number }>("/api/admin/sync", { method: "POST" }),
  reviews: (kind?: "tag" | "match") => api<{ items: ReviewItem[] }>(`/api/admin/reviews${kind ? `?kind=${kind}` : ""}`),
  decide: (body: { id: number; action: "approve" | "reject"; edit?: Record<string, unknown> | null }) =>
    api<ReviewItem>("/api/admin/reviews", { method: "PATCH", body }),
  updateLocation: (id: number, body: LocationAttrsIn) =>
    api<AdminLocation>(`/api/admin/locations/${id}`, { method: "PATCH", body }),
  adminCourses: () => api<{ items: AdminCourse[] }>("/api/admin/courses"),
  draftCourse: (body: CourseDraftIn) => api<AdminCourse>("/api/admin/courses", { method: "POST", body }),
  editCourse: (body: CourseEditIn) => api<AdminCourse>("/api/admin/courses", { method: "PATCH", body }),
  intro: (id: number, spoiler: Spoiler) =>
    api<Intro>(`/api/works/${id}/intro`, { method: "POST", body: { spoiler }, ai: true }),
};
