import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { stationLabel } from "./station";
import { readJson, useStored, writeJson } from "./storage";

describe("storage", () => {
  it("깨진 JSON은 버리고 기본값으로 시작한다", () => {
    window.localStorage.setItem("cl.stamps", "{깨짐");
    expect(readJson("cl.stamps", [])).toEqual([]);
  });
  it("쓰고 읽는다", () => {
    expect(writeJson("cl.courses", [1])).toBe(true);
    expect(readJson("cl.courses", [])).toEqual([1]);
  });
  it("같은 키를 쓰는 다른 컴포넌트에도 바뀐 값이 반영된다(이용 안내 확인 직후 AI 입력이 열림)", () => {
    window.localStorage.removeItem("cl.notice");
    const a = renderHook(() => useStored<string | null>("cl.notice", null));
    const b = renderHook(() => useStored<string | null>("cl.notice", null));
    act(() => a.result.current[1]("v1"));
    expect(b.result.current[0]).toBe("v1");
  });
});

describe("역 이름", () => {
  it("'역'을 두 번 붙이지 않는다", () => {
    expect(stationLabel("남포", "1호선")).toBe("남포역(1호선)");
    expect(stationLabel("부산역", "1호선")).toBe("부산역(1호선)");
    expect(stationLabel("서면")).toBe("서면역");
  });
});
