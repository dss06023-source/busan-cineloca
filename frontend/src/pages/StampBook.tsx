// UI-08 스탬프북(FR-507·509): 이 브라우저의 토큰을 API-017로 확인한 것만 보여 준다.
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { endpoints } from "../api/client";
import { badgeRecords, stampTokens } from "../lib/stamps";

export function StampBook() {
  const tokens = stampTokens();
  const records = badgeRecords();
  const q = useQuery({
    queryKey: ["stampbook", tokens.length, records.length],
    queryFn: () => endpoints.verifyStamps(tokens, records.map((b) => b.token)),
    enabled: tokens.length + records.length > 0,
  });
  const titleOf = (key: string) => {
    for (const b of records) {
      try {
        if (JSON.parse(atob(b.token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).course_key === key) return b.title;
      } catch {
        // 깨진 토큰은 건너뛴다(서버 확인에서 이미 무효로 셈)
      }
    }
    return key.startsWith("course:") ? "추천 코스" : "나만의 코스";
  };

  return (
    <section aria-label="스탬프북">
      <h2>스탬프북</h2>
      <p className="muted">스탬프는 이 브라우저에만 저장됩니다. 브라우저 데이터를 지우거나 기기를 바꾸면 사라집니다.</p>
      {tokens.length + records.length === 0 && (
        <p className="muted">
          아직 스탬프가 없습니다. 촬영지 상세에서 방문 인증을 해 보세요. <Link to="/">지도에서 찾기</Link>
        </p>
      )}
      {q.isLoading && <p className="muted">스탬프를 확인하는 중…</p>}
      {q.isError && <p className="error">{(q.error as Error).message}</p>}
      {q.data && (
        <>
          {q.data.badges.length > 0 && (
            <ul className="list" aria-label="완주 배지">
              {q.data.badges.map((b) => (
                <li key={b.course_key} className="badge-item">
                  🏅 <strong>{titleOf(b.course_key)}</strong>
                  <span className="muted"> · {new Date(b.iat * 1000).toLocaleDateString("ko-KR")} 완주</span>
                </li>
              ))}
            </ul>
          )}
          <p>
            <strong>스탬프 {q.data.valid.length}개</strong>
          </p>
          <ul className="stamp-grid" aria-label="스탬프 목록">
            {q.data.valid.map((s) => (
              <li key={s.location.id} className="stamp">
                <Link to={`/locations/${s.location.id}`}>{s.location.name}</Link>
                {s.work && <span className="muted">{s.work.title}</span>}
                <span className="muted">{new Date(s.iat * 1000).toLocaleDateString("ko-KR")}</span>
              </li>
            ))}
          </ul>
          {q.data.invalid_count > 0 && (
            <p className="notice">확인되지 않은 스탬프·배지 {q.data.invalid_count}개는 표시하지 않았습니다.</p>
          )}
        </>
      )}
    </section>
  );
}
