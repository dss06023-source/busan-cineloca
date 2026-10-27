// GeoProbe: 현재 위치. 좌표는 메모리에만 두고 저장·로그하지 않는다(NFR-003).
export type Position = { lat: number; lon: number; accuracy: number };

export const GEO_TIMEOUT_MS = 5000; // FR-201

export function probe(geo: Geolocation | undefined = navigator.geolocation): Promise<Position | null> {
  if (!geo) return Promise.resolve(null);
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(null), GEO_TIMEOUT_MS + 500);
    geo.getCurrentPosition(
      (p) => {
        clearTimeout(timer);
        resolve({ lat: p.coords.latitude, lon: p.coords.longitude, accuracy: p.coords.accuracy });
      },
      () => {
        clearTimeout(timer);
        resolve(null);
      },
      { enableHighAccuracy: true, timeout: GEO_TIMEOUT_MS, maximumAge: 0 },
    );
  });
}
