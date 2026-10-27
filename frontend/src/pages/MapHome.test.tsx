import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { makeQueryClient, routes } from "../App";
import { NoticeGate } from "../components/NoticeGate";
import { formatDistance } from "./MapHome";

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <NoticeGate>
        <RouterProvider router={router} />
      </NoticeGate>
    </QueryClientProvider>,
  );
}

describe("지도 홈", () => {
  it("위치를 못 얻으면 부산역 기준으로 목록을 보여 주고, 지도 SDK가 없으면 목록 모드로 바뀐다", async () => {
    renderAt("/");
    const list = await screen.findByRole("list", { name: "촬영지 목록" });
    expect(await within(list).findByText("부산역 광장")).toBeTruthy();
    expect(screen.getByText("지도를 불러오지 못해 목록으로 보여 드립니다.")).toBeTruthy();
    expect((screen.getByLabelText("기준 위치") as HTMLSelectElement).value).toBe("s:113");
    expect(screen.getByRole("complementary", { name: "출처" })).toBeTruthy();
  });

  it("항목을 고르면 요약 카드에 작품·거리·역·길찾기 링크가 나온다", async () => {
    renderAt("/");
    const list = await screen.findByRole("list", { name: "촬영지 목록" });
    await userEvent.click(await within(list).findByText("부산역 광장"));
    const card = screen.getByRole("region", { name: "부산역 광장 요약" });
    expect(within(card).getByText("서면 나이트, 부산 추격전")).toBeTruthy();
    // 역은 노선색 배지(노선 이름 + 역 이름)로 보여 준다
    expect(within(card).getByText("1호선")).toBeTruthy();
    expect(within(card).getByText("부산역")).toBeTruthy();
    const link = within(card).getByText("길찾기") as HTMLAnchorElement;
    expect(link.href).toContain("https://map.kakao.com/link/to/");
  });

  it("거리 표기", () => {
    expect(formatDistance(248.4)).toBe("248m");
    expect(formatDistance(1530)).toBe("1.5km");
    expect(formatDistance(null)).toBe("");
  });
});

describe("이용 안내와 상세", () => {
  it("처음 방문하면 안내가 뜨고 확인하면 닫힌다", async () => {
    renderAt("/sources");
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByText("확인했습니다"));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(window.localStorage.getItem("cl.notice")).toBe('"2026-11-01"');
    expect(await screen.findByText(/통합전산망/)).toBeTruthy();
  });

  it("촬영지 상세는 역·도보 시간·작품·출처를 보여 준다", async () => {
    renderAt("/locations/9");
    expect(await screen.findByRole("heading", { name: "부산역 광장" })).toBeTruthy();
    expect(screen.getByText(/걸어서 2분/)).toBeTruthy();
    expect(screen.getByText("서면 나이트")).toBeTruthy();
    expect(screen.getByRole("complementary", { name: "출처" })).toBeTruthy();
  });

  it("없는 촬영지는 안내 문구", async () => {
    renderAt("/locations/999");
    expect(await screen.findByText("찾는 정보가 없습니다.")).toBeTruthy();
  });
});
