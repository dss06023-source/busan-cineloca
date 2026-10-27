import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { makeQueryClient, routes } from "../App";

function renderHome(wide: boolean) {
  vi.stubGlobal("matchMedia", (q: string) => ({ matches: wide, media: q, addEventListener: () => undefined, removeEventListener: () => undefined }));
  const router = createMemoryRouter(routes, { initialEntries: ["/"] });
  render(
    <QueryClientProvider client={makeQueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("첫 화면", () => {
  it("넓은 화면에서는 AI 탐색·지도·작품을 한 화면에 두고, 오른쪽을 코스로 바꿀 수 있다", async () => {
    renderHome(true);
    const ask = screen.getByRole("complementary", { name: "AI 탐색 패널" });
    expect(within(ask).getByLabelText("질문")).toBeTruthy();
    const map = screen.getByRole("region", { name: "지도 패널" });
    expect(await within(map).findByRole("list", { name: "촬영지 목록" })).toBeTruthy();
    const side = screen.getByRole("complementary", { name: "작품·코스 패널" });
    expect(await within(side).findByRole("list", { name: "작품 목록" })).toBeTruthy();
    await userEvent.click(within(side).getByRole("tab", { name: "코스" }));
    expect(within(side).getByRole("tablist", { name: "코스 종류" })).toBeTruthy();
  });

  it("좁은 화면에서는 지도 홈만 보여 준다", async () => {
    renderHome(false);
    expect(await screen.findByRole("list", { name: "촬영지 목록" })).toBeTruthy();
    expect(screen.queryByRole("complementary", { name: "AI 탐색 패널" })).toBeNull();
  });
});
