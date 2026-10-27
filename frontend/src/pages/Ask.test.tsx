import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { makeQueryClient, routes } from "../App";
import { NoticeGate } from "../components/NoticeGate";
import { server } from "../test/server";
import { EXAMPLES } from "./Ask";

function renderAsk(accept = true) {
  if (accept) window.localStorage.setItem("cl.notice", '"2026-11-01"');
  render(
    <QueryClientProvider client={makeQueryClient()}>
      <NoticeGate>
        <RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/ask"] })} />
      </NoticeGate>
    </QueryClientProvider>,
  );
}

describe("AI 탐색(UI-05)", () => {
  it("예시 질의를 3개 이상 보여 주고, 200자를 넘으면 전송을 막는다", async () => {
    renderAsk();
    const examples = screen.getByRole("list", { name: "예시 질의" });
    expect(within(examples).getAllByRole("button").length).toBeGreaterThanOrEqual(3);
    const box = screen.getByLabelText("질문");
    await userEvent.click(box);
    await userEvent.paste("가".repeat(201));
    expect(screen.getByText(/200자 이내로 줄여 주세요/)).toBeTruthy();
    expect((screen.getByText("찾기") as HTMLButtonElement).disabled).toBe(true);
  });

  it("이용 안내를 확인하기 전에는 입력을 막는다", () => {
    renderAsk(false);
    expect((screen.getByLabelText("질문") as HTMLTextAreaElement).disabled).toBe(true);
  });

  it("시연 장면 3: 칩·요약·결과·출처를 보여 주고, 칩을 지우면 그 조건 없이 다시 검색한다", async () => {
    const searched: unknown[] = [];
    server.events.on("request:start", async ({ request }) => {
      if (request.url.endsWith("/api/search")) searched.push(await request.clone().json());
    });
    renderAsk();
    await userEvent.click(screen.getByText(EXAMPLES[0]));
    await userEvent.click(screen.getByText("찾기"));
    const chips = await screen.findByRole("list", { name: "해석한 조건" });
    expect(within(chips).getByText(/강도윤/)).toBeTruthy();
    expect(screen.getByText("AI 생성")).toBeTruthy();
    expect(within(screen.getByRole("list", { name: "검색 결과" })).getByText("부산역 광장")).toBeTruthy();
    expect(screen.getByRole("complementary", { name: "출처" })).toBeTruthy();

    await userEvent.click(screen.getByLabelText("지하철역에서 걸어서 10분 조건 빼기"));
    await screen.findByText("부산역 광장");
    const body = searched.at(-1) as { criteria: Record<string, unknown>; labels: Record<string, string> };
    expect(body.criteria.base_kind).toBeNull();
    expect(body.criteria.person_ids).toEqual([1]);
    expect(body.labels["person_ids:1"]).toBe("강도윤");
    server.events.removeAllListeners();
  });

  it("AI 장애면 안내와 함께 필터 패널을 prefill로 연다", async () => {
    renderAsk();
    await userEvent.type(screen.getByLabelText("질문"), "장애 주입");
    await userEvent.click(screen.getByText("찾기"));
    expect(await screen.findByText(/AI가 질문을 해석하지 못했습니다/)).toBeTruthy();
    const panel = await screen.findByRole("form", { name: "필터 패널" });
    expect(await within(panel).findByLabelText("중구")).toBeTruthy();
    expect((within(panel).getByLabelText("중구") as HTMLInputElement).checked).toBe(true);
  });

  it("분당 한도 초과는 안내 문구", async () => {
    server.use(http.post("/api/query", () => HttpResponse.json({ error: { code: "ERR-011", message: "x", retry_after: 20 } }, { status: 429 })));
    renderAsk();
    await userEvent.type(screen.getByLabelText("질문"), "부산 촬영지");
    await userEvent.click(screen.getByText("찾기"));
    expect(await screen.findByText("요청이 많습니다. 잠시 후 다시 시도해 주세요.")).toBeTruthy();
  });
});
