// UI-04 작품 상세·AI 소개(FR-103~111, FR-707). 관람등급(KOBIS)은 따로 늦게 떠도 된다.
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { ApiError, endpoints, type Intro, type Spoiler } from "../api/client";
import { AiLabel } from "../components/AiLabel";
import { SourceCards } from "../components/SourceCard";

const ROLE: Record<string, string> = { director: "감독", actor: "출연" };

export function WorkDetail() {
  const id = Number(useParams().id);
  const ok = Number.isInteger(id);
  const q = useQuery({ queryKey: ["work", id], queryFn: () => endpoints.work(id), enabled: ok });
  const rating = useQuery({ queryKey: ["rating", id], queryFn: () => endpoints.rating(id), enabled: ok && q.isSuccess });

  if (q.isLoading) return <p className="page muted">불러오는 중…</p>;
  if (q.isError || !q.data) return <p className="page error">{(q.error as Error)?.message ?? "찾는 정보가 없습니다."}</p>;
  const d = q.data;
  const w = d.work;
  const poster = d.images.posters[0];

  return (
    <article className="page">
      <h1>{w.title}</h1>
      <p className="muted">
        {[w.release_year, w.genres.join("·")].filter(Boolean).join(" · ")}
        {rating.data?.rating && <> · 관람등급 {rating.data.rating}</>}
      </p>
      {poster && <img className="photo" src={poster} alt={`${w.title} 포스터`} loading="lazy" />}
      {d.people.length > 0 && (
        <p>
          {d.people.map((p, i) => (
            <span key={`${p.role}-${p.id}`}>
              {i > 0 && ", "}
              {p.name}
              <span className="muted">({ROLE[p.role] ?? p.role})</span>
            </span>
          ))}
        </p>
      )}
      {d.keywords.length > 0 && (
        <ul className="tags" aria-label="키워드">
          {d.keywords.map((k) => (
            <li key={k}>{k}</li>
          ))}
        </ul>
      )}
      {d.kmdb_link && (
        <a href={d.kmdb_link} target="_blank" rel="noreferrer">
          KMDb에서 보기
        </a>
      )}

      <IntroSection workId={w.id} />

      <section>
        <h2>부산 촬영지 {d.locations.length}곳</h2>
        <ul>
          {d.locations.map((l) => (
            <li key={l.id}>
              <Link to={`/locations/${l.id}`}>{l.name}</Link>
              {l.gu && <span className="muted"> ({l.gu})</span>}
              {l.lat == null && <span className="muted"> · 위치 미확인</span>}
            </li>
          ))}
        </ul>
      </section>

      {d.plot && (
        <details>
          <summary>줄거리 보기(스포일러가 있을 수 있음)</summary>
          <p>{d.plot}</p>
        </details>
      )}

      {d.images.stills.length > 0 && <Stills urls={d.images.stills} title={w.title} />}
      {d.vod.length > 0 && (
        <section>
          <h2>예고편</h2>
          <ul>
            {d.vod.map((v) => (
              <li key={v.url}>
                <a href={v.url} target="_blank" rel="noreferrer">
                  {v.title ?? "예고편"}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      {d.related.length > 0 && (
        <section>
          <h2>함께 볼 작품</h2>
          <ul>
            {d.related.map((r) => (
              <li key={r.id}>
                <Link to={`/works/${r.id}`}>{r.title}</Link>
                {r.release_year && <span className="muted"> ({r.release_year})</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
      <SourceCards sources={[...d.sources, ...(rating.data?.sources ?? [])]} />
    </article>
  );
}

function Stills({ urls, title }: { urls: string[]; title: string }) {
  return (
    <section>
      <h2>스틸</h2>
      {urls.slice(0, 3).map((u) => (
        <img key={u} className="photo" src={u} alt={`${title} 스틸`} loading="lazy" />
      ))}
    </section>
  );
}

function IntroSection({ workId }: { workId: number }) {
  const [spoiler, setSpoiler] = useState<Spoiler>("none");
  const intro = useMutation({ mutationFn: (s: Spoiler) => endpoints.intro(workId, s) });

  return (
    <section className="card" aria-label="AI 소개">
      <h2>AI 소개</h2>
      <div className="toolbar">
        <div className="segmented" role="group" aria-label="스포일러 단계">
          <button type="button" aria-pressed={spoiler === "none"} onClick={() => setSpoiler("none")}>
            스포일러 없음
          </button>
          <button type="button" aria-pressed={spoiler === "partial"} onClick={() => setSpoiler("partial")}>
            줄거리 일부 포함
          </button>
        </div>
        <button type="button" className="primary" disabled={intro.isPending} onClick={() => intro.mutate(spoiler)}>
          {intro.isPending ? "만드는 중…" : "AI 소개 보기"}
        </button>
      </div>
      {intro.isError && (
        <p className="error">
          {intro.error instanceof ApiError ? intro.error.message : "요청을 처리하지 못했습니다."}
        </p>
      )}
      {intro.data && <IntroResult r={intro.data} />}
    </section>
  );
}

function IntroResult({ r }: { r: Intro }) {
  if (r.degraded) {
    return (
      <div>
        <AiLabel degraded />
        <p className="notice">AI 소개를 불러오지 못해 기본 정보로 보여 드립니다.</p>
        {r.fallback?.plot && <p>{r.fallback.plot}</p>}
        {r.fallback && r.fallback.locations.length > 0 && (
          <p>부산 촬영지: {r.fallback.locations.map((l) => l.name).join(", ")}</p>
        )}
        <SourceCards sources={r.sources} />
      </div>
    );
  }
  return (
    <div>
      <AiLabel />
      {r.sentences.map((s, i) => (
        <p key={i}>{s}</p>
      ))}
      {r.dropped_count > 0 && <p className="muted">근거와 맞지 않는 문장 {r.dropped_count}개를 뺐습니다.</p>}
      <SourceCards sources={r.sources} />
    </div>
  );
}
