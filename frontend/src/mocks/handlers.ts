// API-001~007·019 목. AI 탐색 목은 WP-09에서 더한다.
import { http, HttpResponse } from "msw";
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
];
