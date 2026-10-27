// UI-01 지도 홈(F2): 기준 위치 → 반경 → 필터 → 지도·거리순 목록 → 요약 카드.
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { endpoints, type MapItem, type SearchIn } from "../api/client";
import { MapView } from "../components/MapView";
import { SourceCards } from "../components/SourceCard";
import { DEFAULT_RADIUS, RADII } from "../config";
import { probe, type Position } from "../lib/geo";
import { directionsUrl } from "../lib/kakao";
import { stationLabel } from "../lib/station";

type BaseChoice = { kind: "here" } | { kind: "station"; id: string } | { kind: "gu"; gu: string };

export function formatDistance(m: number | null | undefined): string {
  if (m == null) return "";
  return m < 1000 ? `${Math.round(m)}m` : `${(m / 1000).toFixed(1)}km`;
}

export function SummaryCard({ item }: { item: MapItem }) {
  const more = item.work_count - item.works.length;
  return (
    <section className="card" aria-label={`${item.name} 요약`}>
      <h3>{item.name}</h3>
      <p>
        {item.works.map((w) => w.title).join(", ")}
        {more > 0 && ` 외 ${more}편`}
      </p>
      <p className="muted">
        {formatDistance(item.distance_m)}
        {item.station && ` · ${stationLabel(item.station.name, item.station.line)}`}
      </p>
      <div className="row">
        <Link to={`/locations/${item.id}`}>상세 보기</Link>
        <a href={directionsUrl(item.name, item.lat, item.lon)} target="_blank" rel="noreferrer">
          길찾기
        </a>
      </div>
    </section>
  );
}

export function MapHome() {
  const meta = useQuery({ queryKey: ["meta"], queryFn: endpoints.meta, staleTime: 10 * 60_000 });
  const [here, setHere] = useState<Position | null | undefined>(undefined);
  const [base, setBase] = useState<BaseChoice | null>(null);
  const [radius, setRadius] = useState<number>(DEFAULT_RADIUS);
  const [genre, setGenre] = useState("");
  const [gu, setGu] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [selected, setSelected] = useState<MapItem | null>(null);
  const [listOnly, setListOnly] = useState(false);

  // FR-201: 위치 권한이 없거나 5초 안에 못 얻으면 부산역
  useEffect(() => {
    probe().then((p) => setHere(p));
  }, []);
  useEffect(() => {
    if (base || here === undefined || !meta.data) return;
    setBase(here ? { kind: "here" } : { kind: "station", id: meta.data.default_station_id });
  }, [base, here, meta.data]);

  const request: SearchIn | null = useMemo(() => {
    if (!base) return null;
    const b =
      base.kind === "here" && here
        ? { lat: here.lat, lon: here.lon }
        : base.kind === "station"
          ? { station_id: base.id }
          : base.kind === "gu"
            ? { gu: base.gu }
            : null;
    if (!b) return null;
    return {
      base: b,
      radius_m: radius as SearchIn["radius_m"],
      filters: {
        genres: genre ? [genre] : null,
        gus: gu ? [gu] : null,
        year_from: yearFrom ? Number(yearFrom) : null,
        year_to: yearTo ? Number(yearTo) : null,
      },
    };
  }, [base, here, radius, genre, gu, yearFrom, yearTo]);

  // 좌표가 담긴 요청이라 쿼리 키에 좌표를 넣지만 저장하지는 않는다(메모리 캐시만)
  const result = useQuery({
    queryKey: ["locations", request],
    queryFn: () => endpoints.searchLocations(request!),
    enabled: request !== null,
  });

  const center = useMemo(() => {
    if (base?.kind === "here" && here) return { lat: here.lat, lon: here.lon };
    const stations = meta.data?.stations ?? [];
    const id = base?.kind === "station" ? base.id : meta.data?.default_station_id;
    const st = stations.find((s) => s.id === id);
    const first = result.data?.items[0];
    if (base?.kind === "gu" && first) return { lat: first.lat, lon: first.lon };
    return st ? { lat: st.lat, lon: st.lon } : { lat: 35.1152, lon: 129.0422 };
  }, [base, here, meta.data, result.data]);

  const onSelect = useCallback((it: MapItem) => setSelected(it), []);
  const onUnavailable = useCallback(() => setListOnly(true), []);
  const items = result.data?.items ?? [];

  return (
    <div className="page">
      <header className="toolbar">
        <label>
          기준
          <select
            aria-label="기준 위치"
            value={base?.kind === "station" ? `s:${base.id}` : base?.kind === "gu" ? `g:${base.gu}` : "here"}
            onChange={(e) => {
              const v = e.target.value;
              setSelected(null);
              setBase(v === "here" ? { kind: "here" } : v.startsWith("s:") ? { kind: "station", id: v.slice(2) } : { kind: "gu", gu: v.slice(2) });
            }}
          >
            <option value="here" disabled={!here}>
              현재 위치{here ? "" : "(사용 불가)"}
            </option>
            <optgroup label="도시철도역">
              {meta.data?.stations.map((s) => (
                <option key={s.id} value={`s:${s.id}`}>
                  {stationLabel(s.name, s.line)}
                </option>
              ))}
            </optgroup>
            <optgroup label="구·군">
              {meta.data?.districts.map((d) => (
                <option key={d} value={`g:${d}`}>
                  {d}
                </option>
              ))}
            </optgroup>
          </select>
        </label>
        <div className="segmented" role="group" aria-label="반경">
          {RADII.map((r) => (
            <button key={r} type="button" aria-pressed={radius === r} disabled={base?.kind === "gu"} onClick={() => setRadius(r)}>
              {r < 1000 ? `${r}m` : `${r / 1000}km`}
            </button>
          ))}
        </div>
        <details className="filters">
          <summary>필터</summary>
          <label>
            장르
            <select value={genre} onChange={(e) => setGenre(e.target.value)}>
              <option value="">전체</option>
              {meta.data?.genres.map((g) => (
                <option key={g}>{g}</option>
              ))}
            </select>
          </label>
          <label>
            구·군
            <select value={gu} onChange={(e) => setGu(e.target.value)}>
              <option value="">전체</option>
              {meta.data?.districts.map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          </label>
          <label>
            개봉연도
            <input inputMode="numeric" placeholder="부터" value={yearFrom} onChange={(e) => setYearFrom(e.target.value.replace(/\D/g, "").slice(0, 4))} />
            <input inputMode="numeric" placeholder="까지" value={yearTo} onChange={(e) => setYearTo(e.target.value.replace(/\D/g, "").slice(0, 4))} />
          </label>
        </details>
      </header>

      {!listOnly && <MapView center={center} items={items} onSelect={onSelect} onUnavailable={onUnavailable} />}
      {listOnly && <p className="notice">지도를 불러오지 못해 목록으로 보여 드립니다.</p>}

      {selected && <SummaryCard item={selected} />}

      {result.isError && <p className="error">{(result.error as Error).message}</p>}
      {result.isLoading && <p className="muted">촬영지를 찾는 중…</p>}
      {result.isSuccess && items.length === 0 && <p className="muted">이 범위에 촬영지가 없습니다. 반경을 넓혀 보세요.</p>}

      <ol className="list" aria-label="촬영지 목록">
        {items.map((it) => (
          <li key={it.id}>
            <button type="button" className="list-item" onClick={() => setSelected(it)}>
              <strong>{it.name}</strong>
              <span className="muted">
                {formatDistance(it.distance_m)} · {it.works.map((w) => w.title).join(", ")}
                {it.work_count > it.works.length && ` 외 ${it.work_count - it.works.length}편`}
              </span>
            </button>
          </li>
        ))}
      </ol>
      <SourceCards sources={result.data?.sources ?? []} />
    </div>
  );
}
