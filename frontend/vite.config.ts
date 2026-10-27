/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// 개발 서버(5173)는 /api를 로컬 백엔드(8000)로 넘긴다. 배포에서는 nginx가 같은 일을 한다.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // e2e/는 Playwright가 돌린다
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
