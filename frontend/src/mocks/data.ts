// 목 데이터: 미니 시드(infra/seed/mini_seed.sql)의 일부와 같은 값. 가짜 데이터다.
import type { LocationDetail, Meta, SearchOut, SourceCard, SourcesOut } from "../api/client";

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
