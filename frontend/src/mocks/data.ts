// 목 데이터: 미니 시드(db/seed/mini_seed.sql)의 일부와 같은 값. 가짜 데이터다.
import type { AdminCourse, AICourseOut, ReviewItem, SyncReport, CourseDetail, CourseList, QueryOut, RouteOut, Intro, LocationDetail, Meta, Rating, SearchOut, SourceCard, SourcesOut, WorkDetail, WorkList } from "../api/client";

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

// API-009~012 코스 목(가짜 데이터)
export const courseList: CourseList = {
  items: [
    { id: 1, theme: "work", title: "부산 추격전 따라 걷기", start_label: "부산역", stop_count: 3, total_min: 104, total_m: 15427 },
    { id: 2, theme: "area", title: "원도심 한 바퀴", start_label: "중앙역", stop_count: 4, total_min: 119, total_m: 2608 },
  ],
};

export const route: RouteOut = {
  start: { label: "부산역", lat: 35.1152, lon: 129.0422 },
  stops: [
    { ord: 1, location_id: 9, name: "부산역 광장", gu: "동구", lat: 35.1152, lon: 129.0422, dwell_min: 20, works: [{ id: 3, title: "부산 추격전", release_year: 2017 }] },
    { ord: 2, location_id: 10, name: "초량 이바구길", gu: "동구", lat: 35.1185, lon: 129.039, dwell_min: 20, works: [] },
    { ord: 3, location_id: 12, name: "광안리 해변", gu: "수영구", lat: 35.1532, lon: 129.1186, dwell_min: 20, works: [{ id: 3, title: "부산 추격전", release_year: 2017 }] },
  ],
  legs: [
    { mode: "walk", minutes: 0, distance_m: 0, line: null },
    { mode: "walk", minutes: 8, distance_m: 451, line: null },
    { mode: "subway", minutes: 36, distance_m: 14976, line: "2호선" },
  ],
  total_min: 104,
  total_m: 15427,
  source_ids: ["DEV-SEED"],
  sources: [dev],
};

export const courseDetail: CourseDetail = { course: courseList.items[0], route };

const aiBase = { preference: null, route: null, reasons: [], intro: null, masked: false, notices: [], reason: null, options: null };
export const aiOk: AICourseOut = {
  ...aiBase,
  status: "OK",
  route,
  intro: { title: "부산역에서 시작하는 추격전 코스", sentences: ["부산 추격전의 추격 장면을 따라 걷습니다.", "마지막은 광안리 바다입니다."], ai_generated: true, dropped_count: 0 },
  reasons: [{ location_id: 12, text: "바다가 보이는 곳이라 골랐습니다." }],
};
export const aiFallback: AICourseOut = {
  ...aiBase,
  status: "FALLBACK",
  options: { genres: ["드라마", "범죄"], mood_tags: ["바다", "야경"], districts: ["중구", "수영구"] },
};
export const aiInfeasible: AICourseOut = { ...aiBase, status: "INFEASIBLE", reason: "budget" };

// API-021·022 관리자 목(가짜)
export const syncReport: SyncReport = {
  runs: [
    { id: 2, trigger: "manual", status: "rejected", requested_by: "admin", counts: { location: 120, work: 40, guard: { ok: false, reason: "촬영지 수가 직전보다 40% 줄었습니다" } }, prev_counts: { location: 200, work: 41 }, guard: { ok: false, reason: "촬영지 수가 직전보다 40% 줄었습니다" }, failures: ["DATA-02: 3회 재시도 실패"] },
    { id: 1, trigger: "manual", status: "published", requested_by: "admin", counts: { location: 200, work: 41 }, prev_counts: null, guard: { ok: true }, failures: [] },
  ],
  usage: { "gemini:gemini-3.5-flash-lite": 12 },
};

export const reviews: ReviewItem[] = [
  { id: 11, kind: "tag", target_type: "location", target_id: 9, target_label: "부산역 광장", proposal: { tags: ["야경", "역"] }, proposer: "ai", model: "fake", score: null, status: "pending" },
  { id: 12, kind: "match", target_type: "work", target_id: 2, target_label: "남포동 블루스", proposal: { kmdb_id: "K99999", title: "남포동 블루스" }, proposer: "rule", model: null, score: 0.72, status: "pending" },
];

// 관리자 추천 코스(API-024) 목
export const adminCourses: AdminCourse[] = [
  {
    id: 3, theme: "area", theme_ref: "해운대구", title: "해운대 바다 촬영지(검토 중)", status: "draft", start_label: "해운대역",
    total_min: 98, total_m: 2513,
    stops: [
      { ord: 1, location_id: 1, name: "해운대해수욕장", leg_mode: "walk", leg_min: 9, leg_line: null },
      { ord: 2, location_id: 2, name: "동백섬", leg_mode: "walk", leg_min: 12, leg_line: null },
      { ord: 3, location_id: 3, name: "더베이101", leg_mode: "walk", leg_min: 17, leg_line: null },
    ],
  },
  {
    id: 1, theme: "work", theme_ref: "3", title: "「부산 추격전」 따라 걷기", status: "approved", start_label: "부산역",
    total_min: 104, total_m: 15427,
    stops: [
      { ord: 1, location_id: 9, name: "부산역 광장", leg_mode: "walk", leg_min: 1, leg_line: null },
      { ord: 2, location_id: 7, name: "광안리해수욕장", leg_mode: "subway", leg_min: 31, leg_line: "1호선→2호선" },
      { ord: 3, location_id: 12, name: "자갈치시장", leg_mode: "subway", leg_min: 12, leg_line: "2호선→1호선" },
    ],
  },
];
