import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { server } from "../test/server";
import { KEYS, writeJson } from "../lib/storage";
import { api, ApiError, NOTICE_REQUIRED_EVENT } from "./client";

describe("api", () => {
  it("모든 요청에 X-Session-Id를, AI 요청에만 X-Notice-Version을 붙인다", async () => {
    const seen: Headers[] = [];
    server.use(
      http.post("/api/x", ({ request }) => {
        seen.push(request.headers);
        return HttpResponse.json({ ok: true });
      }),
    );
    writeJson(KEYS.notice, "2026-11-01");
    await api("/api/x", { method: "POST", body: {} });
    await api("/api/x", { method: "POST", body: {}, ai: true });
    expect(seen[0].get("x-session-id")).toMatch(/^[0-9a-f-]{36}$/);
    expect(seen[0].get("x-session-id")).toBe(seen[1].get("x-session-id"));
    expect(seen[0].get("x-notice-version")).toBeNull();
    expect(seen[1].get("x-notice-version")).toBe("2026-11-01");
  });

  it("오류 코드를 ApiError로 바꾸고 ERR-002면 안내를 다시 띄우게 알린다", async () => {
    server.use(
      http.post("/api/ai", () =>
        HttpResponse.json({ error: { code: "ERR-002", message: "x", retry_after: null } }, { status: 403 }),
      ),
    );
    const listener = vi.fn();
    window.addEventListener(NOTICE_REQUIRED_EVENT, listener);
    const err = (await api("/api/ai", { method: "POST", body: {}, ai: true }).catch((e: unknown) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("ERR-002");
    expect(err.message).toBe("이용 안내를 먼저 확인해 주세요.");
    expect(listener).toHaveBeenCalledOnce();
  });

  it("네트워크 실패는 ERR-015로 다룬다", async () => {
    server.use(http.get("/api/down", () => HttpResponse.error()));
    const err = (await api("/api/down").catch((e: unknown) => e)) as ApiError;
    expect(err.code).toBe("ERR-015");
  });
});
