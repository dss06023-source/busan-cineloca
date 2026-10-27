// UI-02 촬영지 상세(FR-207·209)와 방문 인증 버튼(FR-501~506).
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { endpoints } from "../api/client";
import { CertifyButton } from "../components/CertifyButton";
import { SourceCards } from "../components/SourceCard";
import { directionsUrl } from "../lib/kakao";

const CAUTION_TEXT: Record<string, string> = {
  private: "사유지입니다. 외부에서만 관람해 주세요.",
  residential: "주거지입니다. 외부에서만 조용히 관람해 주세요.",
  school: "학교입니다. 외부에서만 관람해 주세요.",
};

const BLOCK_TEXT: Record<string, string> = {
  no_coords: "위치가 확인되지 않아 방문 인증을 할 수 없습니다.",
  excluded: "관리자가 방문 인증에서 제외한 장소입니다.",
  private: "사유지라 방문 인증을 할 수 없습니다.",
  residential: "주거지라 방문 인증을 할 수 없습니다.",
  school: "학교라 방문 인증을 할 수 없습니다.",
};

export function LocationDetail() {
  const id = Number(useParams().id);
  const q = useQuery({ queryKey: ["location", id], queryFn: () => endpoints.location(id), enabled: Number.isInteger(id) });

  if (q.isLoading) return <p className="page muted">불러오는 중…</p>;
  if (q.isError || !q.data) return <p className="page error">{(q.error as Error)?.message ?? "찾는 정보가 없습니다."}</p>;
  const d = q.data;
  const loc = d.location;

  return (
    <article className="page">
      {CAUTION_TEXT[d.caution] && <p className="warning">{CAUTION_TEXT[d.caution]}</p>}
      {d.safety_note && <p className="warning">{d.safety_note}</p>}
      <h1>{loc.name}</h1>
      <p className="muted">{loc.address ?? "주소 정보 없음"}</p>
      {d.photo && <img className="photo" src={d.photo.url} alt={d.photo.title} loading="lazy" />}
      {d.tags.length > 0 && (
        <ul className="tags">
          {d.tags.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      )}
      {d.station && (
        <p>
          최근접 역: {d.station.name}역({d.station.line}){d.walk_min != null && ` · 걸어서 ${d.walk_min}분`}
        </p>
      )}
      {loc.lat != null && loc.lon != null ? (
        <a className="button" href={directionsUrl(loc.name, loc.lat, loc.lon)} target="_blank" rel="noreferrer">
          카카오맵 길찾기
        </a>
      ) : (
        <p className="muted">위치 미확인</p>
      )}
      <section>
        <h2>이곳에서 촬영한 작품</h2>
        <ul>
          {d.works.map((w) => (
            <li key={w.id}>
              <Link to={`/works/${w.id}`}>{w.title}</Link>
              {w.release_year && <span className="muted"> ({w.release_year})</span>}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2>방문 인증</h2>
        {d.certifiable ? (
          <CertifyButton locationId={loc.id} radius={d.cert_radius_m} />
        ) : (
          <p className="muted">{BLOCK_TEXT[d.cert_block_reason ?? ""] ?? "방문 인증을 할 수 없습니다."}</p>
        )}
      </section>
      <SourceCards sources={d.sources} />
    </article>
  );
}
