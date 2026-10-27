// 브라우저 저장(localStorage). 사생활 보호 모드 등에서 접근이 막히거나 JSON이 깨져도 빈 값으로 시작한다.
import { useCallback, useState } from "react";

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

export function useStored<T>(key: string, fallback: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => readJson(key, fallback));
  const set = useCallback(
    (v: T) => {
      writeJson(key, v);
      setValue(v);
    },
    [key],
  );
  return [value, set];
}
