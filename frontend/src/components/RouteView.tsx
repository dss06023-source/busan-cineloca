// 코스 동선(FR-302·313): 지도 마커, 방문 순서, 구간별 이동 수단·시간, 체류 시간, 총 소요 시간.
import { useState } from "react";
import { Link } from "react-router";
import type { MapItem, RouteOut } from "../api/client";
import { lineColor } from "../lib/station";
import { MapView } from "./MapView";
import { SourceCards } from "./SourceCard";

export function legText(leg: RouteOut["legs"][number]): string {
  return leg.mode === "subway" ? `도시철도 ${leg.line ?? ""} ${leg.minutes}분`.replace("  ", " ") : `걸어서 ${leg.minutes}분`;
}

export function formatMinutes(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h}시간${m ? ` ${m}분` : ""}` : `${m}분`;
}

type Props = {
  route: RouteOut;
  reasons?: Record<number, string>;
  onMove?: (index: number, dir: -1 | 1) => void; // FR-305 순서 바꾸기
};

export function RouteView({ route, reasons = {}, onMove }: Props) {
  const [noMap, setNoMap] = useState(false);
  const items: MapItem[] = route.stops.map((s) => ({
    id: s.location_id, name: `${s.ord}. ${s.name}`, lat: s.lat, lon: s.lon, distance_m: null, works: s.works, work_count: s.works.length, station: null,
  }));
  return (
    <section aria-label="코스 동선">
      <p>
        <strong>총 {formatMinutes(route.total_min)}</strong>
        <span className="muted"> · 이동 {(route.total_m / 1000).toFixed(1)}km · {route.stops.length}곳</span>
      </p>
      {!noMap && <MapView center={{ lat: route.start.lat, lon: route.start.lon }} items={items} onSelect={() => undefined} onUnavailable={() => setNoMap(true)} />}
      <ol className="route">
        <li className="muted">출발: {route.start.label}</li>
        {route.stops.map((s, i) => (
          <li key={`${s.location_id}-${i}`}>
            {/* 도시철도 구간은 노선색 막대로, 걷는 구간은 회색 점선으로 */}
            <p className={route.legs[i].mode === "subway" ? "leg muted subway" : "leg muted"} style={{ borderLeftColor: lineColor(route.legs[i].line)?.bg }}>
              ↓ {legText(route.legs[i])}
            </p>
            <div className="stop">
              <span className="stop-no">{s.ord}</span>
              <div style={{ flex: 1 }}>
                <Link to={`/locations/${s.location_id}`}>{s.name}</Link>
                <span className="muted"> · 머무는 시간 {s.dwell_min}분</span>
                {s.works.length > 0 && <div className="muted">{s.works.map((w) => w.title).join(", ")}</div>}
                {reasons[s.location_id] && <div>{reasons[s.location_id]}</div>}
              </div>
              {onMove && (
                <span className="move">
                  <button type="button" aria-label={`${s.name} 앞으로`} disabled={i === 0} onClick={() => onMove(i, -1)}>
                    ↑
                  </button>
                  <button type="button" aria-label={`${s.name} 뒤로`} disabled={i === route.stops.length - 1} onClick={() => onMove(i, 1)}>
                    ↓
                  </button>
                </span>
              )}
            </div>
          </li>
        ))}
      </ol>
      <SourceCards sources={route.sources} />
    </section>
  );
}
