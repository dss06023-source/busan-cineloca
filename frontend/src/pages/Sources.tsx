// UI-09 데이터 출처·이용 안내(FR-705).
import { useQuery } from "@tanstack/react-query";
import { endpoints } from "../api/client";

const POLICY_TEXT: Record<string, string> = { STORE: "저장", ID_ONLY: "식별자만 저장", NO_STORE: "저장 안 함" };

export function Sources() {
  const q = useQuery({ queryKey: ["sources"], queryFn: endpoints.sources, staleTime: 10 * 60_000 });
  return (
    <article className="page">
      <h1>데이터 출처·이용 안내</h1>
      {q.isError && <p className="error">{(q.error as Error).message}</p>}
      <ul className="ledger">
        {q.data?.sources.map((s) => (
          <li key={s.id}>
            <a href={s.url} target="_blank" rel="noreferrer">
              {s.org} · {s.name}
            </a>
            <div className="muted">
              {s.license} · {POLICY_TEXT[s.policy] ?? s.policy}
              {s.base_date && ` · 기준일 ${s.base_date}`}
            </div>
          </li>
        ))}
      </ul>
      {q.data && <p>{q.data.kobis_notice}</p>}
      <h2>위치와 개인정보</h2>
      <p>현재 위치는 검색과 방문 인증에만 쓰고 서버에 저장하지 않습니다. 스탬프와 저장 코스는 이 브라우저에만 저장됩니다.</p>
    </article>
  );
}
