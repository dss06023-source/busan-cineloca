// 브라우저 저장(localStorage). 사생활 보호 모드 등에서 접근이 막히거나 JSON이 깨져도 빈 값으로 시작한다.
import { useCallback, useEffect, useState } from "react";

export const KEYS = {
  stamps: "cl.stamps",
  badges: "cl.badges",
  courses: "cl.courses",
  favorites: "cl.favorites",
  notice: "cl.notice",
} as const;

export function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

export function writeJson(key: string, value: unknown): boolean {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

// 같은 탭의 다른 컴포넌트에 바뀐 값을 알린다(브라우저의 storage 이벤트는 다른 탭에만 온다)
const CHANGED = "cl:stored";

export function useStored<T>(key: string, fallback: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => readJson(key, fallback));
  useEffect(() => {
    const reload = (e: Event) => {
      const changed = e instanceof StorageEvent ? e.key : (e as CustomEvent<string>).detail;
      if (changed === key) setValue(readJson(key, fallback));
    };
    window.addEventListener(CHANGED, reload);
    window.addEventListener("storage", reload);
    return () => {
      window.removeEventListener(CHANGED, reload);
      window.removeEventListener("storage", reload);
    };
    // fallback은 처음 값으로만 쓴다(호출마다 새 객체여도 다시 구독하지 않음)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  const set = useCallback(
    (v: T) => {
      writeJson(key, v);
      setValue(v);
      window.dispatchEvent(new CustomEvent(CHANGED, { detail: key }));
    },
    [key],
  );
  return [value, set];
}
