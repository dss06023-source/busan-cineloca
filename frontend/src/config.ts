// 이용 안내 버전(서버 NOTICE_VERSION과 같게 둔다). 다르면 안내를 다시 띄운다.
export const NOTICE_VERSION: string = import.meta.env.VITE_NOTICE_VERSION ?? "2026-11-01";
export const RADII = [500, 1000, 3000] as const;
export const DEFAULT_RADIUS = 1000;
