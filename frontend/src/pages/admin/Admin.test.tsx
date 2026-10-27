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

describe("추천 코스 관리(UI-12)", () => {
  it("순서 바꾸기는 범위 안에서만", async () => {
    const { move } = await import("./AdminCourses");
    expect(move([1, 2, 3], 0, 1)).toEqual([2, 1, 3]);
    expect(move([1, 2, 3], 0, -1)).toEqual([1, 2, 3]);
  });

  it("목록, 순서 바꿔 다시 계산하면 초안, 승인 버튼", async () => {
    let sent: unknown = null;
    server.use(
      http.patch("/api/admin/courses", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ error: { code: "ERR-001", message: "입력 값을 확인해 주세요(테스트)" } }, { status: 422 });
      }),
    );
    renderAt("/admin/courses");
    const card = await screen.findByRole("listitem", { name: "코스 3" });
    expect(within(card).getByText("초안")).toBeTruthy();
    expect(within(screen.getByRole("listitem", { name: "코스 1" })).getByText("공개")).toBeTruthy();
    await userEvent.click(within(card).getByRole("button", { name: "동백섬 위로" }));
    const names = within(within(card).getByRole("list", { name: "장소 순서" })).getAllByRole("listitem").map((li) => li.textContent);
    expect(names[0]).toMatch(/^동백섬/);
    expect(within(card).getByRole("button", { name: "승인" })).toHaveProperty("disabled", true);
    await userEvent.click(within(card).getByRole("button", { name: "이 순서로 다시 계산" }));
    expect(await within(card).findByText(/테스트/)).toBeTruthy();
    expect(sent).toEqual({ id: 3, stops: [2, 1, 3] });
  });

  it("후보 만들기: 실패하면 이유, 성공하면 안내", async () => {
    renderAt("/admin/courses");
    const form = await screen.findByRole("form", { name: "코스 후보 만들기" });
    const input = within(form).getByPlaceholderText(/구·군 이름/);
    await userEvent.type(input, "없는구");
    await userEvent.click(within(form).getByRole("button", { name: "후보 만들기" }));
    expect(await within(form).findByText(/0곳뿐이라/)).toBeTruthy();
    await userEvent.clear(input);
    await userEvent.type(input, "중구");
    await userEvent.click(within(form).getByRole("button", { name: "후보 만들기" }));
    expect(await within(form).findByText("초안을 만들었습니다: 중구 촬영지 산책")).toBeTruthy();
  });
});
