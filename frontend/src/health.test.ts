import { describe, expect, it } from "vitest";
import { describeHealth } from "./health";

describe("describeHealth", () => {
  it("API에 닿지 않으면 연결 불가로 안내한다", () => {
    expect(describeHealth(null)).toBe("API에 연결할 수 없습니다");
  });
  it("db 상태에 따라 문구가 바뀐다", () => {
    expect(describeHealth({ db: "ok", ai_breakers: {}, gemini_usage: {} })).toBe("서비스 정상");
    expect(describeHealth({ db: "down", ai_breakers: {}, gemini_usage: null })).toBe("데이터베이스 연결 확인 필요");
  });
});
