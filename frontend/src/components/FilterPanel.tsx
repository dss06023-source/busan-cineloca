// FilterPanel(UI-05, FR-410·411): AI 없이 같은 검색 템플릿(API-014). AI가 강등되면 prefill로 채워서 연다.
import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { endpoints, type Criteria } from "../api/client";
import { stationLabel } from "../lib/station";

const WALK_MINUTES = [5, 10, 15, 20, 30];

type Props = {
  initial: Criteria;
  labels: Record<string, string>;
  onSearch: (c: Criteria) => void;
  busy?: boolean;
};

export function FilterPanel({ initial, labels, onSearch, busy = false }: Props) {
  const meta = useQuery({ queryKey: ["meta"], queryFn: endpoints.meta, staleTime: Infinity });
  const [c, setC] = useState<Criteria>(initial);
  const station = c.base_kind === "station" ? (c.station_id ?? "") : c.base_kind === "any_station" ? "*" : "";

  function toggle(field: "genres" | "gus", v: string) {
    const cur = c[field] ?? [];
    const next = cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v];
    setC({ ...c, [field]: next.length ? next : null });
  }

  function setStation(v: string) {
    if (!v) setC({ ...c, base_kind: null, station_id: null, travel_mode: null, travel_min: null });
    else if (v === "*") setC({ ...c, base_kind: "any_station", station_id: null, travel_mode: "walk", travel_min: c.travel_min ?? 10 });
    else setC({ ...c, base_kind: "station", station_id: v, travel_mode: "walk", travel_min: c.travel_min ?? 10 });
  }

  function year(field: "year_from" | "year_to", v: string) {
    const n = Number(v);
    setC({ ...c, [field]: v && n >= 1900 && n <= 2100 ? n : null });
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    onSearch(c);
  }

  const fixed = [
    ...(c.work_ids ?? []).map((id) => ({ field: "work_ids" as const, id, label: labels[`work_ids:${id}`] ?? `작품 ${id}` })),
    ...(c.person_ids ?? []).map((id) => ({ field: "person_ids" as const, id, label: labels[`person_ids:${id}`] ?? `인물 ${id}` })),
  ];

  return (
    <form className="card filters" aria-label="필터 패널" onSubmit={submit}>
      <h2>조건 직접 고르기</h2>
      {fixed.length > 0 && (
        <ul className="tags" aria-label="작품·인물">
          {fixed.map((f) => (
            <li key={`${f.field}-${f.id}`}>
              {f.label}{" "}
              <button
                type="button"
                aria-label={`${f.label} 빼기`}
                onClick={() => {
                  const rest = (c[f.field] ?? []).filter((x) => x !== f.id);
                  setC({ ...c, [f.field]: rest.length ? rest : null });
                }}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <fieldset>
        <legend>장르</legend>
        <div className="checks">
          {meta.data?.genres.map((g) => (
            <label key={g}>
              <input type="checkbox" checked={c.genres?.includes(g) ?? false} onChange={() => toggle("genres", g)} />
              {g}
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend>구·군</legend>
        <div className="checks">
          {meta.data?.districts.map((g) => (
            <label key={g}>
              <input type="checkbox" checked={c.gus?.includes(g) ?? false} onChange={() => toggle("gus", g)} />
              {g}
            </label>
          ))}
        </div>
      </fieldset>
      <label>
        개봉연도
        <input aria-label="개봉연도 시작" inputMode="numeric" value={c.year_from ?? ""} onChange={(e) => year("year_from", e.target.value)} />~
        <input aria-label="개봉연도 끝" inputMode="numeric" value={c.year_to ?? ""} onChange={(e) => year("year_to", e.target.value)} />
      </label>
      <label>
        기준 역
        <select aria-label="기준 역" value={station} onChange={(e) => setStation(e.target.value)}>
          <option value="">정하지 않음</option>
          <option value="*">아무 지하철역</option>
          {meta.data?.stations.map((s) => (
            <option key={s.id} value={s.id}>
              {stationLabel(s.name, s.line)}
            </option>
          ))}
        </select>
      </label>
      {station && (
        <label>
          걸어서
          <select
            aria-label="도보 시간"
            value={c.travel_min ?? 10}
            onChange={(e) => setC({ ...c, travel_mode: "walk", travel_min: Number(e.target.value) })}
          >
            {WALK_MINUTES.map((m) => (
              <option key={m} value={m}>
                {m}분
              </option>
            ))}
          </select>
          안
        </label>
      )}
      <button type="submit" className="primary" disabled={busy}>
        {busy ? "찾는 중…" : "이 조건으로 찾기"}
      </button>
    </form>
  );
}
