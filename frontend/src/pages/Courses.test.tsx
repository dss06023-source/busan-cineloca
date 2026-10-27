import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
import { makeQueryClient, routes } from "../App";
import { NoticeGate } from "../components/NoticeGate";
import { legText, formatMinutes } from "../components/RouteView";
import { listSaved, MAX_SAVED, saveCourse } from "../lib/savedCourses";
import * as data from "../mocks/data";

const stopNames = (el: HTMLElement) =>
  within(el)
    .getAllByRole("link")
    .filter((a) => a.getAttribute("href")?.startsWith("/locations/"))
    .map((a) => a.textContent);

function renderAt(path: string) {
  window.localStorage.setItem("cl.notice", '"2026-11-01"');
  render(
    <QueryClientProvider client={makeQueryClient()}>
      <NoticeGate>
        <RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />
      </NoticeGate>
    </QueryClientProvider>,
  );
}

beforeEach(() => window.localStorage.clear());

describe("코스(UI-06·07)", () => {
  it("구간 문구와 시간 표기", () => {
    expect(legText({ mode: "subway", minutes: 36, distance_m: 1, line: "2호선" })).toBe("도시철도 2호선 36분");
    expect(legText({ mode: "walk", minutes: 8, distance_m: 1, line: null })).toBe("걸어서 8분");
    expect(formatMinutes(104)).toBe("1시간 44분");
    expect(formatMinutes(120)).toBe("2시간");
    expect(formatMinutes(45)).toBe("45분");
  });

  it("추천 코스 목록에서 상세로 가면 순서·구간·총 시간을 보여 준다", async () => {
    renderAt("/courses");
    const list = await screen.findByRole("list", { name: "추천 코스 목록" });
    expect(await within(list).findAllByRole("link")).toHaveLength(2);
    await userEvent.click(within(list).getByText("부산 추격전 따라 걷기"));
    expect(await screen.findByRole("heading", { name: "부산 추격전 따라 걷기" })).toBeTruthy();
    expect(screen.getByText("총 1시간 44분")).toBeTruthy();
    expect(screen.getByText(/도시철도 2호선 36분/)).toBeTruthy();
  });

  it("저장은 10개까지이고, 넘으면 지우지 않고 거절한다(FR-306)", () => {
    for (let i = 0; i < MAX_SAVED; i++) expect(saveCourse({ route: data.route, title: `c${i}`, kind: "custom" })).not.toBeNull();
    expect(saveCourse({ route: data.route, title: "넘침", kind: "custom" })).toBeNull();
    expect(listSaved()).toHaveLength(MAX_SAVED);
    expect(listSaved().some((c) => c.title === "c0")).toBe(true);
  });

  it("나만의 코스: 2곳 이상 골라 동선을 만들고, 순서를 바꾸면 그 순서로 다시 계산한다", async () => {
    renderAt("/courses?tab=custom");
    const group = await screen.findByRole("group", { name: "촬영지 고르기" });
    const make = screen.getByRole("button", { name: "동선 만들기" }) as HTMLButtonElement;
    await userEvent.click(await within(group).findByLabelText("부산역 광장"));
    expect(make.disabled).toBe(true);
    await userEvent.click(within(group).getByLabelText("초량 이바구길"));
    await userEvent.click(make);
    const stops = await screen.findByRole("region", { name: "코스 동선" });
    expect(stopNames(stops)).toEqual(["부산역 광장", "초량 이바구길"]);
    await userEvent.click(within(stops).getByRole("button", { name: "부산역 광장 뒤로" }));
    await screen.findByRole("button", { name: "초량 이바구길 뒤로" });
    const after = screen.getByRole("region", { name: "코스 동선" });
    expect(stopNames(after)).toEqual(["초량 이바구길", "부산역 광장"]);
    await userEvent.click(screen.getByRole("button", { name: "이 코스 저장" }));
    expect(await screen.findByRole("list", { name: "저장한 코스" })).toBeTruthy();
  });

  it("AI 맞춤: 소개에 AI 표시와 고른 이유를 보여 준다", async () => {
    renderAt("/courses?tab=ai");
    await userEvent.type(screen.getByLabelText("취향"), "바다 보이는 곳");
    await userEvent.click(screen.getByRole("button", { name: "AI 코스 만들기" }));
    expect(await screen.findByRole("heading", { name: "부산역에서 시작하는 추격전 코스" })).toBeTruthy();
    expect(screen.getByText("바다가 보이는 곳이라 골랐습니다.")).toBeTruthy();
    expect(screen.getByText("AI 생성")).toBeTruthy();
  });

  it("AI 맞춤: AI를 못 쓰면 조건 직접 고르기로 이어 간다", async () => {
    renderAt("/courses?tab=ai");
    await userEvent.type(screen.getByLabelText("취향"), "장애");
    await userEvent.click(screen.getByRole("button", { name: "AI 코스 만들기" }));
    const form = await screen.findByLabelText("조건 직접 고르기");
    await userEvent.click(within(form).getByLabelText("바다"));
    await userEvent.click(within(form).getByRole("button", { name: "이 조건으로 코스 만들기" }));
    expect(await screen.findByRole("heading", { name: "부산역에서 시작하는 추격전 코스" })).toBeTruthy();
  });

  it("AI 맞춤: 시간이 모자라면 이유를 알려 준다", async () => {
    renderAt("/courses?tab=ai");
    await userEvent.type(screen.getByLabelText("취향"), "1분 코스");
    await userEvent.click(screen.getByRole("button", { name: "AI 코스 만들기" }));
    expect(await screen.findByText(/시간을 늘려 주세요/)).toBeTruthy();
  });
});
