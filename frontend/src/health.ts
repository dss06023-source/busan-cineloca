// API-025 상태 확인. WP-04가 ApiClient(openapi-typescript 타입)로 바꾼다.
export type Health = { db: string; ai_breakers: Record<string, string>; gemini_usage: Record<string, number> | null };

export function describeHealth(h: Health | null): string {
  if (h === null) return "API에 연결할 수 없습니다";
  return h.db === "ok" ? "서비스 정상" : "데이터베이스 연결 확인 필요";
}

export async function fetchHealth(): Promise<Health | null> {
  try {
    const res = await fetch("/api/health");
    return (await res.json()) as Health;
  } catch {
    return null;
  }
}
