import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { makeQueryClient, routes } from "../App";
import { failText } from "../components/CertifyButton";
import { stampTokens } from "../lib/stamps";

function renderAt(path: string) {
  render(
    <QueryClientProvider client={makeQueryClient()}>
      <RouterProvider router={createMemoryRouter(routes, { initialEntries: [path] })} />
    </QueryClientProvider>,
  );
}

function fakeGeo(accuracy: number | null) {
  const geo = {
    getCurrentPosition: (ok: PositionCallback, fail: PositionErrorCallback) =>
      accuracy === null
        ? fail({ code: 1 } as GeolocationPositionError)
        : ok({ coords: { latitude: 35.1153, longitude: 129.0422, accuracy } } as GeolocationPosition),
  };
  vi.stubGlobal("navigator", { ...navigator, geolocation: geo });
}

afterEach(() => vi.unstubAllGlobals());

describe("방문 인증·스탬프북(UI-02·08)", () => {
  it("실패 이유별 안내 문구", () => {
    expect(failText({ ok: false, token: null, reason: "distance", distance_m: 140 }, 100)).toMatch(/약 140m.*100m 안으로/);
    expect(failText({ ok: false, token: null, reason: "accuracy", distance_m: 3 }, 100)).toMatch(/실외/);
    expect(failText({ ok: false, token: null, reason: "duplicate", distance_m: 3 }, 100)).toMatch(/이미/);
  });

  it("인증하면 토큰만 저장하고 좌표는 저장하지 않는다", async () => {
    fakeGeo(12);
    renderAt("/locations/9");
    await userEvent.click(await screen.findByRole("button", { name: "방문 인증하기" }));
    expect(await screen.findByText(/스탬프를 받았습니다/)).toBeTruthy();
    expect(stampTokens()).toEqual(["m.9.s"]);
    expect(JSON.stringify({ ...window.localStorage })).not.toMatch(/35\.1153|129\.0422/);
  });

  it("정확도가 낮으면 실외에서 다시 하라고 안내한다", async () => {
    fakeGeo(80);
    renderAt("/locations/9");
    await userEvent.click(await screen.findByRole("button", { name: "방문 인증하기" }));
    expect(await screen.findByText(/실외로 나가/)).toBeTruthy();
    expect(stampTokens()).toEqual([]);
  });

  it("위치 권한이 없으면 안내한다", async () => {
    fakeGeo(null);
    renderAt("/locations/9");
    await userEvent.click(await screen.findByRole("button", { name: "방문 인증하기" }));
    expect(await screen.findByText(/위치 권한을 허용/)).toBeTruthy();
  });

  it("스탬프북은 서버가 확인한 것만 보여 주고, 기기를 바꾸면 사라진다고 알린다", async () => {
    window.localStorage.setItem("cl.stamps", JSON.stringify(["m.9.s", "m.10.s", "forged"]));
    window.localStorage.setItem("cl.badges", JSON.stringify([{ token: "m.course:1.b", title: "부산 추격전 따라 걷기" }]));
    renderAt("/me");
    const list = await screen.findByRole("list", { name: "스탬프 목록" });
    expect(within(list).getAllByRole("link").map((a) => a.textContent)).toEqual(["부산역 광장", "초량 이바구길"]);
    expect(screen.getByText(/확인되지 않은 스탬프·배지 1개/)).toBeTruthy();
    expect(within(screen.getByRole("list", { name: "완주 배지" })).getByText("추천 코스")).toBeTruthy();
    expect(screen.getByText(/기기를 바꾸면 사라집니다/)).toBeTruthy();
  });

  it("완주 배지: 빠진 곳을 알려 주고, 다 모으면 배지를 저장한다", async () => {
    window.localStorage.setItem("cl.stamps", JSON.stringify(["m.9.s", "m.10.s"]));
    renderAt("/courses/1");
    await userEvent.click(await screen.findByRole("button", { name: "완주 배지 받기" }));
    expect(await screen.findByText(/아직 인증하지 않은 곳: 광안리 해변/)).toBeTruthy();
    window.localStorage.setItem("cl.stamps", JSON.stringify(["m.9.s", "m.10.s", "m.12.s"]));
    await userEvent.click(screen.getByRole("button", { name: "완주 배지 받기" }));
    expect(await screen.findByText(/완주 배지를 받았습니다/)).toBeTruthy();
    expect(JSON.parse(window.localStorage.getItem("cl.badges")!)).toEqual([{ token: "m.course:1.b", title: "부산 추격전 따라 걷기" }]);
  });
});
