// API-001~023 목. 목 모드에서 질문에 '장애'가 들어가면 AI 강등 응답을 돌려준다.
import { http, HttpResponse } from "msw";
import type { QueryOut } from "../api/client";
import * as data from "./data";

export const handlers = [
  http.get("/api/meta", () => HttpResponse.json(data.meta)),
  http.post("/api/locations/search", () => HttpResponse.json(data.search)),
  http.get("/api/locations/:id", ({ params }) =>
    Number(params.id) === data.location.location.id
      ? HttpResponse.json(data.location)
      : HttpResponse.json({ error: { code: "HTTP-404", message: "없음", retry_after: null } }, { status: 404 }),
  ),
  http.get("/api/sources", () => HttpResponse.json(data.sources)),
  http.get("/api/works", () => HttpResponse.json(data.works)),
  http.get("/api/works/:id", ({ params }) =>
    Number(params.id) === data.work.work.id
      ? HttpResponse.json(data.work)
      : HttpResponse.json({ error: { code: "HTTP-404", message: "없음", retry_after: null } }, { status: 404 }),
  ),
  http.get("/api/works/:id/rating", () => HttpResponse.json(data.rating)),
  // VITE_USE_MOCKS 화면 확인용: '일부' 단계는 강등 응답을 돌려 강등 화면을 볼 수 있게 한다
  http.post("/api/works/:id/intro", async ({ request }) => {
    const body = (await request.json()) as { spoiler: string };
    return HttpResponse.json(body.spoiler === "partial" ? data.introDegraded : data.introOk);
  }),
  http.post("/api/query", async ({ request }) => {
    const body = (await request.json()) as { text: string };
    return HttpResponse.json(body.text.includes("장애") ? data.queryFallback : data.queryScene3);
  }),
  // 필터 패널·칩 삭제: 보낸 조건을 그대로 돌려주고 결과는 장면 3 목록
  http.post("/api/search", async ({ request }) => {
    const body = (await request.json()) as { criteria: QueryOut["criteria"] };
    const chips = data.queryScene3.chips.filter((c) => (c.field === "travel" ? body.criteria?.base_kind : body.criteria?.person_ids));
    return HttpResponse.json({ ...data.queryScene3, summary: null, chips, criteria: body.criteria });
  }),
  http.get("/api/courses", () => HttpResponse.json(data.courseList)),
  http.get("/api/courses/:id", ({ params }) =>
    Number(params.id) === data.courseDetail.course.id
      ? HttpResponse.json(data.courseDetail)
      : HttpResponse.json({ error: { code: "HTTP-404", message: "없음", retry_after: null } }, { status: 404 }),
  ),
  // 고른 순서대로 정류장을 돌려준다(목은 위치 9·10·12만 안다)
  http.post("/api/courses/plan", async ({ request }) => {
    const body = (await request.json()) as { location_ids: number[] };
    const stops = body.location_ids
      .map((id) => data.route.stops.find((s) => s.location_id === id))
      .filter((s) => s !== undefined)
      .map((s, i) => ({ ...s, ord: i + 1 }));
    return HttpResponse.json({ ...data.route, stops, legs: data.route.legs.slice(0, stops.length) });
  }),
  // '장애'는 직접 고르기, '1분'은 시간 부족
  http.post("/api/courses/ai", async ({ request }) => {
    const body = (await request.json()) as { preference?: string; manual?: unknown };
    if (body.manual) return HttpResponse.json(data.aiOk);
    if (body.preference?.includes("장애")) return HttpResponse.json(data.aiFallback);
    if (body.preference?.includes("1분")) return HttpResponse.json(data.aiInfeasible);
    return HttpResponse.json(data.aiOk);
  }),
  // 방문 인증 목: 정확도 50m 초과면 accuracy, 이미 가진 곳이면 duplicate. 토큰은 가짜 형식 m.<장소>.s
  http.post("/api/stamps", async ({ request }) => {
    const b = (await request.json()) as { location_id: number; accuracy_m: number; held: string[] };
    if (b.accuracy_m > 50) return HttpResponse.json({ ok: false, token: null, reason: "accuracy", distance_m: 12 });
    if (b.held.includes(`m.${b.location_id}.s`)) return HttpResponse.json({ ok: false, token: null, reason: "duplicate", distance_m: 12 });
    return HttpResponse.json({ ok: true, token: `m.${b.location_id}.s`, reason: null, distance_m: 12 });
  }),
  http.post("/api/stamps/verify", async ({ request }) => {
    const b = (await request.json()) as { tokens: string[]; badges: string[] };
    const known = Object.fromEntries(data.search.items.map((i) => [i.id, i]));
    const ids = b.tokens.map((t) => Number(/^m\.(\d+)\.s$/.exec(t)?.[1])).filter((id) => known[id]);
    const badges = b.badges.filter((t) => t.startsWith("m.course:")).map((t) => ({ course_key: t.slice(2, -2), iat: 1793000000 }));
    return HttpResponse.json({
      valid: ids.map((id) => ({ location: { id, name: known[id].name, gu: "동구" }, work: known[id].works[0] ?? null, iat: 1793000000 })),
      invalid_count: b.tokens.length - ids.length + b.badges.length - badges.length,
      badges,
    });
  }),
  http.post("/api/badges", async ({ request }) => {
    const b = (await request.json()) as { course: { id?: number }; stamps: string[] };
    const missing = data.route.stops.map((s) => s.location_id).filter((id) => !b.stamps.includes(`m.${id}.s`));
    const key = `course:${b.course.id ?? "x"}`;
    return HttpResponse.json(missing.length ? { ok: false, token: null, course_key: key, missing } : { ok: true, token: `m.${key}.b`, course_key: key, missing: [] });
  }),
  // 관리자 목: 비밀번호 'demo'만 통과, '잠금'은 423
  http.post("/api/admin/session", async ({ request }) => {
    const { password } = (await request.json()) as { password: string };
    if (password === "demo") return new HttpResponse(null, { status: 204 });
    const locked = password === "잠금";
    return HttpResponse.json(
      { error: { code: "ERR-012", message: "관리자 인증에 실패했습니다", retry_after: locked ? 540 : null } },
      { status: locked ? 423 : 401 },
    );
  }),
  http.delete("/api/admin/session", () => new HttpResponse(null, { status: 204 })),
  http.get("/api/admin/sync", () => HttpResponse.json(data.syncReport)),
  http.post("/api/admin/sync", () => HttpResponse.json({ run_id: 3 }, { status: 202 })),
  http.get("/api/admin/reviews", () => HttpResponse.json({ items: data.reviews })),
  http.patch("/api/admin/reviews", async ({ request }) => {
    const b = (await request.json()) as { id: number; action: string };
    const item = data.reviews.find((r) => r.id === b.id)!;
    return HttpResponse.json({ ...item, status: b.action === "approve" ? "approved" : "rejected" });
  }),
  http.patch("/api/admin/locations/:id", async ({ request, params }) => {
    const b = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      id: Number(params.id), name: "부산역 광장", caution: b.caution ?? "none", safety_note: b.safety_note ?? null,
      cert_radius_m: b.cert_radius_m ?? 100, cert_excluded: b.cert_excluded ?? false, tags: ["역"],
    });
  }),
  http.get("/api/admin/courses", () => HttpResponse.json({ items: data.adminCourses })),
  http.post("/api/admin/courses", async ({ request }) => {
    const b = (await request.json()) as { theme: string; ref: string; title?: string | null };
    if (b.ref === "없는구") {
      return HttpResponse.json({ error: { code: "ERR-001", message: "입력 값을 확인해 주세요(좌표가 있는 촬영지가 0곳뿐이라 코스를 만들 수 없습니다)" } }, { status: 422 });
    }
    return HttpResponse.json({ ...data.adminCourses[0], id: 10, theme: b.theme, theme_ref: b.ref, title: b.title || `${b.ref} 촬영지 산책` }, { status: 201 });
  }),
  http.patch("/api/admin/courses", async ({ request }) => {
    const b = (await request.json()) as { id: number; stops?: number[] | null; status?: string | null };
    const c = data.adminCourses.find((x) => x.id === b.id) ?? data.adminCourses[0];
    const stops = b.stops ? b.stops.map((id, i) => ({ ...c.stops.find((s) => s.location_id === id)!, ord: i + 1 })) : c.stops;
    return HttpResponse.json({ ...c, stops, status: b.stops ? "draft" : (b.status ?? c.status) });
  }),
  http.delete("/api/query/session", () => new HttpResponse(null, { status: 204 })),
];
