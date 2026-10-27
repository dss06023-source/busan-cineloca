// 저장 코스(FR-306): 브라우저에만 최대 10개. 서버에 보내지 않는다.
import type { RouteOut } from "../api/client";
import { KEYS, readJson, writeJson } from "./storage";

export const MAX_SAVED = 10;

export type SavedCourse = {
  key: string;
  title: string;
  kind: "custom" | "ai" | "recommended";
  savedAt: string;
  route: RouteOut;
};

export function listSaved(): SavedCourse[] {
  const v = readJson<SavedCourse[]>(KEYS.courses, []);
  return Array.isArray(v) ? v : [];
}

// 가득 차면 false. 오래된 것을 몰래 지우지 않는다
export function saveCourse(c: Omit<SavedCourse, "key" | "savedAt">): SavedCourse | null {
  const all = listSaved();
  if (all.length >= MAX_SAVED) return null;
  const saved: SavedCourse = { ...c, key: crypto.randomUUID(), savedAt: new Date().toISOString() };
  return writeJson(KEYS.courses, [saved, ...all]) ? saved : null;
}

export function removeSaved(key: string): void {
  writeJson(
    KEYS.courses,
    listSaved().filter((c) => c.key !== key),
  );
}

export function getSaved(key: string): SavedCourse | undefined {
  return listSaved().find((c) => c.key === key);
}
