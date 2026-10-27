// 목 데이터: 미니 시드(infra/seed/mini_seed.sql)의 일부와 같은 값. 가짜 데이터다.
import type { QueryOut, Intro, LocationDetail, Meta, Rating, SearchOut, SourceCard, SourcesOut, WorkDetail, WorkList } from "../api/client";

const dev: SourceCard = {
  id: "DEV-SEED",
  org: "부산 씨네로케 팀",
  name: "개발용 미니 시드(가짜 데이터)",
  base_date: "2026-10-27",
  url: "https://github.com/dss06023-source/busan-cineloca",
};
const coord: SourceCard = { id: "DATA-06", org: "행정안전부", name: "실시간 주소정보 조회·좌표 제공", base_date: null, url: "https://www.data.go.kr/data/15057017/openapi.do" };
const station: SourceCard = { id: "DATA-08", org: "부산교통공사", name: "도시철도 역사정보", base_date: null, url: "https://www.data.go.kr/data/15158991/openapi.do" };

export const stations: Meta["stations"] = [
  { id: "113", name: "부산역", line: "1호선", lat: 35.1152, lon: 129.0422, gu: "동구" },
  { id: "119", name: "서면", line: "1호선", lat: 35.1579, lon: 129.0594, gu: "부산진구" },
  { id: "203", name: "해운대", line: "2호선", lat: 35.1634, lon: 129.1586, gu: "해운대구" },
];

export const meta: Meta = {
  districts: ["중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구", "해운대구", "사하구", "금정구", "강서구", "연제구", "수영구", "사상구", "기장군"],
  stations,
  genres: ["드라마", "범죄", "액션", "코미디"],
  year_range: [2001, 2022],
  default_station_id: "113",
};

export const search: SearchOut = {
  items: [
    { id: 9, name: "부산역 광장", lat: 35.1152, lon: 129.0422, distance_m: 0, works: [{ id: 4, title: "서면 나이트", release_year: 2021 }, { id: 3, title: "부산 추격전", release_year: 2017 }], work_count: 2, station: stations[0] },
    { id: 10, name: "초량 이바구길", lat: 35.1185, lon: 129.039, distance_m: 451, works: [], work_count: 0, station: null },
  ],
  source_ids: ["DATA-06", "DATA-08", "DEV-SEED"],
  sources: [coord, station, dev],
};

export const location: LocationDetail = {
  location: { id: 9, name: "부산역 광장", address: "부산 동구 초량동", gu: "동구", lat: 35.1152, lon: 129.0422 },
  photo: null,
  tags: ["역"],
  station: stations[0],
  walk_min: 2,
  works: search.items[0].works,
  caution: "none",
  safety_note: null,
  certifiable: true,
  cert_block_reason: null,
  cert_radius_m: 100,
  source_ids: ["DATA-06", "DATA-08", "DEV-SEED"],
  sources: [coord, station, dev],
};

export const sources: SourcesOut = {
  sources: [{ ...dev, license: "개발용", policy: "STORE" }],
  licenses: [{ source_id: "DEV-SEED", license: "개발용", policy: "STORE" }],
  kobis_notice: "이 서비스는 영화진흥위원회 영화관입장권 통합전산망의 오픈 API를 이용합니다.",
};

export const works: WorkList = {
  items: [
    { id: 3, title: "부산 추격전", release_year: 2017, genres: ["범죄", "액션"], location_count: 3 },
    { id: 9, title: "북항 작전", release_year: 2022, genres: ["액션", "스릴러"], location_count: 2 },
    { id: 2, title: "남포동 블루스", release_year: 2001, genres: ["드라마", "범죄"], location_count: 2 },
  ],
  total: 3,
  page: 1,
};

export const work: WorkDetail = {
  work: works.items[0],
  people: [{ id: 1, name: "강도윤", role: "actor" }],
  plot: "형사 강도윤은 부산역에서 사라진 증인을 쫓아 도시 곳곳을 달린다.",
  keywords: ["추격", "형사", "부산역"],
  images: { posters: [], stills: [] },
  vod: [],
  kmdb_link: null,
  locations: [
    { id: 9, name: "부산역 광장", gu: "동구", lat: 35.1152, lon: 129.0422 },
    { id: 11, name: "가상 골목", gu: "중구", lat: null, lon: null },
  ],
  related: [{ id: 9, title: "북항 작전", release_year: 2022 }],
  source_ids: ["DEV-SEED"],
  sources: [dev],
};

export const rating: Rating = { rating: null, source_ids: [], sources: [] };

const gemini: SourceCard = { id: "DATA-11", org: "Google", name: "Gemini API(무료 티어)", base_date: null, url: "https://ai.google.dev" };

export const introOk: Intro = {
  status: "ok",
  sentences: ["「부산 추격전」(2017)은 범죄 액션 영화입니다.", "동구의 부산역 광장에서 촬영했습니다."],
  ai_generated: true,
  degraded: false,
  fallback: null,
  dropped_count: 1,
  source_ids: ["DEV-SEED", "DATA-11"],
  sources: [dev, gemini],
};

// AI 장애 때의 강등 응답(FR-110, NFR-002)
export const introDegraded: Intro = {
  status: "degraded",
  sentences: [],
  ai_generated: false,
  degraded: true,
  fallback: { plot: work.plot, locations: work.locations.map(({ id, name, gu }) => ({ id, name, gu })) },
  dropped_count: 0,
  source_ids: ["DEV-SEED"],
  sources: [dev],
};

const queryBase = () => ({ choices: [], notices: [], works: [], relaxed: [], masked: false, prefill: null });

// 시연 장면 3(미니 시드의 가짜 인물 강도윤)
export const queryScene3: QueryOut = {
  ...queryBase(),
  status: "OK",
  chips: [
    { field: "person_ids", label: "강도윤" },
    { field: "travel", label: "지하철역에서 걸어서 10분" },
  ],
  criteria: { person_ids: [1], base_kind: "any_station", travel_mode: "walk", travel_min: 10, result_type: "LOCATION" },
  labels: { "person_ids:1": "강도윤" },
  items: [
    { id: 9, name: "부산역 광장", gu: "동구", lat: 35.1152, lon: 129.0422, distance_m: null, travel_min: 2, works: [{ id: 3, title: "부산 추격전", release_year: 2017 }] },
    { id: 4, name: "자갈치시장", gu: "중구", lat: 35.0966, lon: 129.0306, distance_m: null, travel_min: 3, works: [{ id: 9, title: "북항 작전", release_year: 2022 }] },
  ],
  summary: { sentences: ["강도윤 출연작 촬영지 2곳이 역에서 걸어서 10분 안에 있습니다."], ai_generated: true, dropped_count: 0 },
  source_ids: ["DATA-08", "DATA-11", "DEV-SEED"],
  sources: [station, gemini, dev],
};

// AI 장애: 필터 패널을 직전 조건으로 채운다(FR-411)
export const queryFallback: QueryOut = {
  ...queryBase(),
  status: "FALLBACK",
  chips: [],
  criteria: null,
  labels: {},
  items: [],
  summary: null,
  prefill: { gus: ["중구"], result_type: "LOCATION" },
  source_ids: [],
  sources: [],
};
