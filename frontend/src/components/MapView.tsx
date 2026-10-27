// 카카오 지도 + 묶음 마커(FR-204). SDK를 못 불러오면 onUnavailable을 불러 목록 모드로 바꾼다.
// 마커는 카카오 기본 핀 대신 원: 일반은 fg, 고른 것은 accent, AI 결과는 ai(DESIGN.md). 색은 CSS 토큰에서 읽는다.
/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from "react";
import type { MapItem } from "../api/client";
import { loadKakao } from "../lib/kakao";

type Props = {
  center: { lat: number; lon: number };
  items: MapItem[];
  selectedId?: number | null;
  tone?: "default" | "ai";
  onSelect: (item: MapItem) => void;
  onUnavailable: () => void;
};

function token(name: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

function dot(kakao: any, fill: string, size: number) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><circle cx="${size / 2}" cy="${size / 2}" r="${size / 2 - 2}" fill="${fill}" stroke="#fff" stroke-width="2"/></svg>`;
  return new kakao.maps.MarkerImage(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`, new kakao.maps.Size(size, size), {
    offset: new kakao.maps.Point(size / 2, size / 2),
  });
}

export function MapView({ center, items, selectedId = null, tone = "default", onSelect, onUnavailable }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<any>(null);
  const clusterer = useRef<any>(null);
  const markers = useRef<Map<number, any>>(new Map());
  const [kakao, setKakao] = useState<any>(null);

  useEffect(() => {
    let alive = true;
    loadKakao().then((k) => {
      if (!alive) return;
      if (!k || !box.current) return onUnavailable();
      map.current = new k.maps.Map(box.current, { center: new k.maps.LatLng(center.lat, center.lon), level: 5 });
      // 요약 카드가 왼쪽 아래에 뜨므로 카카오 로고·축척은 오른쪽 아래로(FR-706: 가리지 않음)
      map.current.setCopyrightPosition?.(k.maps.CopyrightPosition.BOTTOMRIGHT, true);
      clusterer.current = new k.maps.MarkerClusterer({
        map: map.current,
        averageCenter: true,
        minLevel: 4,
        styles: [
          {
            width: "36px", height: "36px", lineHeight: "32px", textAlign: "center", borderRadius: "50%",
            background: token("--fg", "#000"), color: token("--bg", "#fff"), border: "2px solid #fff",
            fontFamily: '"Barlow Condensed", sans-serif', fontWeight: "600", fontSize: "16px",
          },
        ],
      });
      setKakao(k);
    });
    return () => {
      alive = false;
    };
    // 지도는 한 번만 만든다
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!kakao || !map.current) return;
    map.current.setCenter(new kakao.maps.LatLng(center.lat, center.lon));
  }, [kakao, center.lat, center.lon]);

  useEffect(() => {
    if (!kakao || !clusterer.current) return;
    clusterer.current.clear();
    markers.current.clear();
    const base = dot(kakao, tone === "ai" ? token("--ai", "#3346c4") : token("--fg", "#000"), 18);
    const list = items.map((it) => {
      const m = new kakao.maps.Marker({ position: new kakao.maps.LatLng(it.lat, it.lon), title: it.name, image: base });
      kakao.maps.event.addListener(m, "click", () => onSelect(it));
      markers.current.set(it.id, m);
      return m;
    });
    clusterer.current.addMarkers(list);
  }, [kakao, items, tone, onSelect]);

  // 목록에서 고른 행과 지도 마커를 함께 켠다
  useEffect(() => {
    if (!kakao) return;
    const base = dot(kakao, tone === "ai" ? token("--ai", "#3346c4") : token("--fg", "#000"), 18);
    const on = dot(kakao, token("--accent", "#d42a33"), 26);
    markers.current.forEach((m, id) => {
      m.setImage(id === selectedId ? on : base);
      m.setZIndex(id === selectedId ? 10 : 0);
    });
    const picked = selectedId != null ? markers.current.get(selectedId) : null;
    if (picked && map.current) map.current.panTo(picked.getPosition());
  }, [kakao, items, selectedId, tone]);

  return <div ref={box} className="map" role="region" aria-label="촬영지 지도" />;
}
