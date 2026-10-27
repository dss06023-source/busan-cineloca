// API-005·006·007·019 목. AI API 목(강등 응답 포함)은 WP-08·09에서 더한다.
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
];
