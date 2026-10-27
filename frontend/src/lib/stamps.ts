// 스탬프·배지 토큰(FR-504·508). 서버가 준 토큰만 브라우저에 둔다. 좌표는 넣지 않는다.
import { KEYS, readJson, writeJson } from "./storage";

export type BadgeRecord = { token: string; title: string };

function strings(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

export function stampTokens(): string[] {
  return strings(readJson<unknown>(KEYS.stamps, []));
}

export function addStamp(token: string): boolean {
  const all = stampTokens();
  return all.includes(token) || writeJson(KEYS.stamps, [...all, token]);
}

export function badgeRecords(): BadgeRecord[] {
  const v = readJson<unknown>(KEYS.badges, []);
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is BadgeRecord => typeof x?.token === "string" && typeof x?.title === "string");
}

export function addBadge(rec: BadgeRecord): boolean {
  const all = badgeRecords();
  return all.some((b) => b.token === rec.token) || writeJson(KEYS.badges, [...all, rec]);
}
