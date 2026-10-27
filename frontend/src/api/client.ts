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

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string | undefined,
    public retryAfter: number | null = null,
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
  try {
    const err = (await res.json()).error;
    code = err?.code;
    retryAfter = err?.retry_after ?? null;
  } catch {
    code = res.status >= 500 ? "ERR-016" : undefined;
  }
  if (code === "ERR-002") window.dispatchEvent(new Event(NOTICE_REQUIRED_EVENT));
  throw new ApiError(res.status, code, retryAfter);
}

export const endpoints = {
  searchLocations: (body: SearchIn) => api<SearchOut>("/api/locations/search", { method: "POST", body }),
  location: (id: number) => api<LocationDetail>(`/api/locations/${id}`),
  meta: () => api<Meta>("/api/meta"),
  sources: () => api<SourcesOut>("/api/sources"),
};
