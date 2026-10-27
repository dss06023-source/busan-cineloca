// 카카오 지도 SDK를 한 번만 불러온다. 키가 없거나 도메인 미등록 등으로 실패하면 null(목록 모드, SRS D2).
// 카카오 응답은 화면에만 쓰고 저장·캐시하지 않는다(DATA-07 NO_STORE).
/* eslint-disable @typescript-eslint/no-explicit-any */
declare global {
  interface Window {
    kakao?: any;
  }
}

let loading: Promise<any | null> | null = null;

export function loadKakao(appKey: string | undefined = import.meta.env.VITE_KAKAO_JS_KEY): Promise<any | null> {
  if (!appKey) return Promise.resolve(null);
  if (window.kakao?.maps?.LatLng) return Promise.resolve(window.kakao);
  loading ??= new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(appKey)}&autoload=false&libraries=clusterer`;
    script.async = true;
    script.onload = () => {
      if (!window.kakao?.maps) return resolve(null);
      window.kakao.maps.load(() => resolve(window.kakao));
    };
    script.onerror = () => resolve(null);
    document.head.appendChild(script);
  });
  return loading;
}

// FR-208 길찾기 링크
export function directionsUrl(name: string, lat: number, lon: number): string {
  return `https://map.kakao.com/link/to/${encodeURIComponent(name)},${lat},${lon}`;
}
