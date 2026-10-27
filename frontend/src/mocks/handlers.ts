// API-001~007·013~015·019 목. 목 모드에서 질문에 '장애'가 들어가면 AI 강등 응답을 돌려준다.
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
  http.delete("/api/query/session", () => new HttpResponse(null, { status: 204 })),
];
