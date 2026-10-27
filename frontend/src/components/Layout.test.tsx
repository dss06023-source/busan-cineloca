import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider, type RouteObject } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { makeQueryClient, routes } from "../App";
import { Layout, pageTitle } from "./Layout";
import { RouteError } from "./RouteError";

function renderAt(entries: string[], rs: RouteObject[] = routes) {
  const router = createMemoryRouter(rs, { initialEntries: entries, initialIndex: entries.length - 1 });
  render(
    <QueryClientProvider client={makeQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

describe("공통 레이아웃", () => {
  it("상세 화면에 바로 들어오면 뒤로 가기가 목록으로 간다", async () => {
    const router = renderAt(["/works/2"]);
    await userEvent.click(await screen.findByRole("button", { name: "← 뒤로" }));
    expect(router.state.location.pathname).toBe("/works");
  });

  it("앱 안에서 넘어왔으면 뒤로 가기가 이전 화면으로 간다", async () => {
    const router = renderAt(["/"]);
    await router.navigate("/locations/1");
    await userEvent.click(await screen.findByRole("button", { name: "← 뒤로" }));
    expect(router.state.location.pathname).toBe("/");
  });

  it("탭 화면에는 뒤로 가기가 없고, 브라우저 탭 제목을 화면 이름으로 바꾼다", async () => {
    renderAt(["/works"]);
    await screen.findByRole("heading", { name: "작품" });
    expect(screen.queryByRole("button", { name: "← 뒤로" })).toBeNull();
    expect(document.title).toBe("작품 · 부산 씨네로케");
    expect(pageTitle("/courses/saved/abc")).toBe("코스 · 부산 씨네로케");
    expect(pageTitle("/admin")).toBe("부산 씨네로케");
  });

  it("첫 화면 3단에 들어 있는 메뉴는 넓은 화면에서 숨길 수 있게 표시하고, 내 기록은 남긴다", async () => {
    renderAt(["/me"]);
    const nav = await screen.findByRole("navigation", { name: "주 메뉴" });
    expect(within(nav).getByRole("link", { name: "작품" }).className).toContain("merged");
    expect(within(nav).getByRole("link", { name: "내 기록" }).className).not.toContain("merged");
    expect(within(nav).getByRole("link", { name: "부산 씨네로케" }).getAttribute("href")).toBe("/");
  });

  it("없는 주소는 안내와 홈 링크를 보여 준다", async () => {
    renderAt(["/nope"]);
    expect(await screen.findByRole("heading", { name: "페이지를 찾을 수 없습니다" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "지도 홈으로" })).toBeTruthy();
  });

  it("화면이 오류를 던져도 하단 탭은 남고 한국어 안내가 뜬다", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    function Boom(): never {
      throw new Error("boom");
    }
    renderAt(["/"], [{ element: <Layout />, children: [{ errorElement: <RouteError />, children: [{ path: "/", element: <Boom /> }] }] }]);
    expect(await screen.findByRole("heading", { name: "화면을 표시하지 못했습니다" })).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "주 메뉴" })).toBeTruthy();
    vi.restoreAllMocks();
  });
});
