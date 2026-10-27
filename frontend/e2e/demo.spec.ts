// 시연 장면 5개(build-plan 1장). 미니 시드(가짜 데이터)와 가짜 AI 응답(backend factory.FAKE_RESPONSES)에 맞춘 기대값이다.
import { expect, test, type Page } from "@playwright/test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

// 부산역 광장(미니 시드 35.1152, 129.0422) 근처. 로그 감사에서 찾을 수 있게 자릿수를 늘린 값
const HERE = { latitude: 35.115234, longitude: 129.042187, accuracy: 10 };

async function acceptNotice(page: Page) {
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "확인했습니다" }).click();
  await expect(dialog).toBeHidden();
}

test("장면 1: 지도 홈에서 해운대 주변 촬영지", async ({ page }) => {
  await page.goto("/");
  await acceptNotice(page);
  await page.getByLabel("기준 위치").selectOption({ label: "해운대역(2호선)" });
  const list = page.getByRole("list", { name: "촬영지 목록" });
  await expect(list.getByText("해운대해수욕장")).toBeVisible();
  await expect(page.getByRole("complementary", { name: "출처" })).toBeVisible();
});

test("장면 2: 작품 상세와 AI 소개", async ({ page }) => {
  await page.goto("/works/3");
  await acceptNotice(page);
  await expect(page.getByRole("heading", { name: "부산 추격전" })).toBeVisible();
  const intro = page.getByRole("region", { name: "AI 소개" });
  await intro.getByRole("button", { name: "AI 소개 보기" }).click();
  await expect(intro.getByText("형사 강도윤이 부산역에서 사라진 증인을 쫓습니다.")).toBeVisible();
  await expect(intro.getByText("AI 생성")).toBeVisible();
});

test("장면 3: AI 탐색(인물 + 역에서 걸어서 10분)", async ({ page }) => {
  await page.goto("/ask");
  await acceptNotice(page);
  await page.getByText("강도윤 나온 영화 촬영지 중 지하철역에서 걸어서 10분 안").click();
  await page.getByRole("button", { name: "찾기" }).click();
  await expect(page.getByRole("list", { name: "해석한 조건" }).getByText(/강도윤/)).toBeVisible();
  await expect(page.getByRole("list", { name: "검색 결과" }).getByText("부산역 광장")).toBeVisible();
  await expect(page.getByText("AI 생성").first()).toBeVisible();
});

test("장면 4: AI 맞춤 코스(서면 출발 반나절)", async ({ page }) => {
  await page.goto("/courses");
  await acceptNotice(page);
  await page.getByRole("tab", { name: "AI 맞춤" }).click();
  await page.getByLabel("취향").fill("서면 출발 반나절, 야경 좋은 곳");
  await page.getByRole("button", { name: "AI 코스 만들기" }).click();
  await expect(page.getByRole("heading", { name: "서면에서 출발하는 촬영지 반나절" })).toBeVisible();
  await expect(page.getByRole("region", { name: "코스 동선" })).toBeVisible();
});

test("장면 5: 방문 인증과 스탬프북, 좌표는 로그에 남지 않음", async ({ page, context }) => {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation(HERE);
  await page.goto("/locations/9");
  await acceptNotice(page);
  await page.getByRole("button", { name: "방문 인증하기" }).click();
  await expect(page.getByText(/스탬프를 받았습니다/)).toBeVisible();
  await page.goto("/me");
  await expect(page.getByRole("list", { name: "스탬프 목록" }).getByText("부산역 광장")).toBeVisible();

  // NFR-003: 위치를 보낸 요청 뒤에도 API 로그에 그 좌표가 없어야 한다(E2E_LOG_DIR이 있을 때)
  const dir = process.env.E2E_LOG_DIR;
  if (dir) {
    const logs = readdirSync(dir).filter((f) => f.endsWith(".jsonl")).map((f) => readFileSync(join(dir, f), "utf-8")).join("");
    expect(logs).not.toContain(String(HERE.latitude));
    expect(logs).not.toContain(String(HERE.longitude));
  }
});
