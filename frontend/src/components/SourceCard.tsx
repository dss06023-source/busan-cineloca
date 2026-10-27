// 출처 카드(FR-704, NFR-008): 외부 데이터나 AI 문장이 나오는 영역에 빠짐없이 붙인다.
import type { SourceCard as Card } from "../api/client";

export function SourceCards({ sources }: { sources: Card[] }) {
  if (sources.length === 0) return null;
  return (
    <aside className="sources" aria-label="출처">
      <span className="sources-title">출처</span>
      <ul>
        {sources.map((s) => (
          <li key={s.id}>
            <a href={s.url} target="_blank" rel="noreferrer">
              {s.org} · {s.name}
            </a>
            {s.base_date && <span className="muted"> (기준일 {s.base_date})</span>}
          </li>
        ))}
      </ul>
    </aside>
  );
}
