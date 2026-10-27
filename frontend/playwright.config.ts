// E2E(build-plan 8장): 시연 장면 5개를 360px·1440px에서 돌린다. 백엔드는 미니 시드 DB와 가짜 AI(AI_PROVIDERS=fake)로 띄운다.
// 실행: e2e/run.sh (DB 준비 → 백엔드·vite 기동 → npx playwright test). CI의 PR 검사에는 넣지 않는다.
import { defineConfig, devices } from "@playwright/test";

const API_PORT = Number(process.env.E2E_API_PORT ?? 8000);
const WEB_PORT = Number(process.env.E2E_WEB_PORT ?? 5173);

export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    locale: "ko-KR",
    timezoneId: "Asia/Seoul",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "mobile-360", use: { ...devices["Pixel 5"], viewport: { width: 360, height: 740 } } },
    { name: "desktop-1440", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
  ],
  webServer: [
    {
      command: `cd ../backend && .venv/bin/uvicorn app.main:app --port ${API_PORT}`,
      url: `http://localhost:${API_PORT}/api/health`,
      reuseExistingServer: true,
      env: { AI_PROVIDERS: "fake", FAKE_AI_MODE: "ok", DATABASE_URL: process.env.E2E_DATABASE_URL ?? "", LOG_DIR: process.env.E2E_LOG_DIR ?? "logs" },
    },
    {
      command: `npx vite --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: true,
    },
  ],
});
