import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { makeQueryClient, routes } from "../../App";
import { server } from "../../test/server";
import { parseTags } from "./AdminReviews";

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <QueryClientProvider client={makeQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

describe("관리자 화면(UI-10·11)", () => {
  it("태그 입력을 쉼표·공백으로 나누고 중복을 뺀다", () => {
    expect(parseTags("야경, 역  광장,역")).toEqual(["야경", "역", "광장"]);
  });

  it("로그인: 틀리면 안내, 잠기면 남은 시간, 맞으면 동기화 화면으로", async () => {
    const router = renderAt("/admin/login");
    const box = screen.getByLabelText("비밀번호");
    await userEvent.type(box, "x");
    await userEvent.click(screen.getByRole("button", { name: "로그인" }));
    expect(await screen.findByText(/5회 틀리면 10분/)).toBeTruthy();
    await userEvent.clear(box);
    await userEvent.type(box, "잠금");
    await userEvent.click(screen.getByRole("button", { name: "로그인" }));
    expect(await screen.findByText(/약 9분 뒤/)).toBeTruthy();
    await userEvent.clear(box);
    await userEvent.type(box, "demo");
    await userEvent.click(screen.getByRole("button", { name: "로그인" }));
    expect(await screen.findByRole("heading", { name: "동기화" })).toBeTruthy();
    expect(router.state.location.pathname).toBe("/admin/sync");
  });

  it("동기화 리포트: 가드 위반 경고, 직전 건수, 실패 목록, AI 호출 수", async () => {
    renderAt("/admin/sync");
    const runs = await screen.findByRole("list", { name: "동기화 기록" });
    expect(within(runs).getByText(/건수 가드 위반: 촬영지 수가 직전보다 40% 줄었습니다/)).toBeTruthy();
    expect(within(runs).getByText(/location 120 \(직전 200\)/)).toBeTruthy();
    expect(within(runs).getByText("실패 1건")).toBeTruthy();
    expect(screen.getByText(/gemini-3.5-flash-lite 12회/)).toBeTruthy();
  });

  it("로그인이 풀리면(401) 로그인 화면으로 보낸다", async () => {
    server.use(
      http.get("/api/admin/reviews", () =>
        HttpResponse.json({ error: { code: "ERR-012", message: "x", retry_after: null } }, { status: 401 }),
      ),
    );
    const router = renderAt("/admin/reviews");
    expect(await screen.findByRole("heading", { name: "관리자 로그인" })).toBeTruthy();
    expect(router.state.location.pathname).toBe("/admin/login");
  });

  it("검수: 고친 태그로 승인 요청을 보내고, 촬영지 속성을 저장한다", async () => {
    let sent: unknown = null;
    server.use(
      http.patch("/api/admin/reviews", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ status: "approved" });
      }),
    );
    renderAt("/admin/reviews");
    const card = await screen.findByRole("listitem", { name: "검수 11" });
    expect(within(card).getByText(/AI\(fake\)/)).toBeTruthy();
    const input = within(card).getByLabelText("태그(쉼표로 구분)");
    await userEvent.clear(input);
    await userEvent.type(input, "야경, 광장");
    await userEvent.click(within(card).getByRole("button", { name: "승인" }));
    await screen.findByRole("listitem", { name: "검수 11" });
    expect(sent).toEqual({ id: 11, action: "approve", edit: { tags: ["야경", "광장"] } });

    const form = screen.getByRole("form", { name: "촬영지 속성 편집" });
    await userEvent.type(within(form).getByLabelText("촬영지 ID"), "9");
    await userEvent.selectOptions(within(form).getByLabelText("주의 구분"), "private");
    await userEvent.click(within(form).getByRole("button", { name: "저장" }));
    expect(await within(form).findByText(/저장했습니다: 부산역 광장 · private/)).toBeTruthy();
  });
});
