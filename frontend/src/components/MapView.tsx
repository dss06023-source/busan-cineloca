// 카카오 지도 + 묶음 마커(FR-204). SDK를 못 불러오면 onUnavailable을 불러 목록 모드로 바꾼다.
/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from "react";
import type { MapItem } from "../api/client";
import { loadKakao } from "../lib/kakao";

type Props = {
  center: { lat: number; lon: number };
  items: MapItem[];
  onSelect: (item: MapItem) => void;
  onUnavailable: () => void;
};

export function MapView({ center, items, onSelect, onUnavailable }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<any>(null);
  const clusterer = useRef<any>(null);
  const [kakao, setKakao] = useState<any>(null);

  useEffect(() => {
    let alive = true;
    loadKakao().then((k) => {
      if (!alive) return;
      if (!k || !box.current) return onUnavailable();
      map.current = new k.maps.Map(box.current, { center: new k.maps.LatLng(center.lat, center.lon), level: 5 });
      clusterer.current = new k.maps.MarkerClusterer({ map: map.current, averageCenter: true, minLevel: 4 });
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
    const markers = items.map((it) => {
      const m = new kakao.maps.Marker({ position: new kakao.maps.LatLng(it.lat, it.lon), title: it.name });
      kakao.maps.event.addListener(m, "click", () => onSelect(it));
      return m;
    });
    clusterer.current.addMarkers(markers);
  }, [kakao, items, onSelect]);

  return <div ref={box} className="map" role="region" aria-label="촬영지 지도" />;
}
