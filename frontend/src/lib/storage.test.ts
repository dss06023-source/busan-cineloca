import { describe, expect, it } from "vitest";
import { readJson, writeJson } from "./storage";

describe("storage", () => {
  it("깨진 JSON은 버리고 기본값으로 시작한다", () => {
    window.localStorage.setItem("cl.stamps", "{깨짐");
    expect(readJson("cl.stamps", [])).toEqual([]);
  });
  it("쓰고 읽는다", () => {
    expect(writeJson("cl.courses", [1])).toBe(true);
    expect(readJson("cl.courses", [])).toEqual([1]);
  });
});
