// 화면 폭 조건을 구독한다. matchMedia가 없으면(테스트 환경 등) false.
import { useSyncExternalStore } from "react";

export const WIDE_QUERY = "(min-width: 1100px)";

export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      if (typeof window.matchMedia !== "function") return () => undefined;
      const m = window.matchMedia(query);
      m.addEventListener("change", onChange);
      return () => m.removeEventListener("change", onChange);
    },
    () => (typeof window.matchMedia === "function" ? window.matchMedia(query).matches : false),
  );
}
