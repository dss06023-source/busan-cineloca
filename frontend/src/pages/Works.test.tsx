import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { makeQueryClient, routes } from "../App";
import { NoticeGate } from "../components/NoticeGate";
import * as data from "../mocks/data";
import { server } from "../test/server";

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <QueryClientProvider client={makeQueryClient()}>
      <NoticeGate>
        <RouterProvider router={router} />
      </NoticeGate>
    </QueryClientProvider>,
  );
  return router;
}

function acceptNotice() {
  window.localStorage.setItem("cl.notice", '"2026-11-01"');
}

describe("작품 목록(UI-03)", () => {
  it("목록과 촬영지 수를 보여 주고, 검색·정렬이 요청 조건으로 간다", async () => {
    const seen: string[] = [];
    server.use(
      http.get("/api/works", ({ request }) => {
        seen.push(new URL(request.url).search);
        return HttpResponse.json(data.works);
      }),
    );
    acceptNotice();
    const router = renderAt("/works");
    const list = await screen.findByRole("list", { name: "작품 목록" });
    expect(within(list).getByText("부산 추격전")).toBeTruthy();
    expect(within(list).getByText(/부산 촬영지 3곳/)).toBeTruthy();
    await userEvent.type(screen.getByLabelText("제목 검색"), "추격");
    await userEvent.click(screen.getByText("검색"));
    await userEvent.click(screen.getByText("최신 개봉 순"));
    expect(router.state.location.search).toBe("?q=%EC%B6%94%EA%B2%A9&sort=year");
    expect(seen.at(-1)).toContain("sort=year");
  });
});

describe("작품 상세(UI-04)", () => {
  it("인물·키워드·촬영지·관련 작품·출처를 보여 준다", async () => {
    acceptNotice();
    renderAt("/works/3");
    expect(await screen.findByRole("heading", { name: "부산 추격전" })).toBeTruthy();
    expect(screen.getByText("강도윤")).toBeTruthy();
    expect(screen.getByText("부산역 광장")).toBeTruthy();
    expect(screen.getByText("· 위치 미확인", { exact: false })).toBeTruthy();
    expect(screen.getByText("북항 작전")).toBeTruthy();
    expect(screen.getByRole("complementary", { name: "출처" })).toBeTruthy();
  });

  it("AI 소개: 정상이면 'AI 생성'과 문장, 강등이면 기본 정보와 안내", async () => {
    acceptNotice();
    renderAt("/works/3");
    const section = await screen.findByRole("region", { name: "AI 소개" });
    await userEvent.click(within(section).getByText("AI 소개 보기"));
    expect(await within(section).findByText("AI 생성")).toBeTruthy();
    expect(within(section).getByText("동구의 부산역 광장에서 촬영했습니다.")).toBeTruthy();
    expect(within(section).getByText(/1개를 뺐습니다/)).toBeTruthy();

    await userEvent.click(within(section).getByText("줄거리 일부 포함"));
    await userEvent.click(within(section).getByText("AI 소개 보기"));
    expect(await within(section).findByText("기본 정보로 대체됨")).toBeTruthy();
    expect(within(section).getByText(/AI 소개를 불러오지 못해/)).toBeTruthy();
    expect(within(section).getByText(/부산 촬영지: 부산역 광장, 가상 골목/)).toBeTruthy();
  });

  it("AI 소개 요청에 이용 안내 버전을 붙이고, 분당 한도 초과는 안내 문구", async () => {
    let notice: string | null = null;
    server.use(
      http.post("/api/works/:id/intro", ({ request }) => {
        notice = request.headers.get("X-Notice-Version");
        return HttpResponse.json({ error: { code: "ERR-011", message: "x", retry_after: 30 } }, { status: 429 });
      }),
    );
    acceptNotice();
    renderAt("/works/3");
    const section = await screen.findByRole("region", { name: "AI 소개" });
    await userEvent.click(within(section).getByText("AI 소개 보기"));
    expect(await within(section).findByText("요청이 많습니다. 잠시 후 다시 시도해 주세요.")).toBeTruthy();
    expect(notice).toBe("2026-11-01");
  });

  it("없는 작품은 안내 문구", async () => {
    acceptNotice();
    renderAt("/works/999");
    expect(await screen.findByText("찾는 정보가 없습니다.")).toBeTruthy();
  });
});
