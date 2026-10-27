// 해석 조건(Criteria) 다루기: 칩 삭제(FR-412)와 후보 선택(FR-403)은 조건을 고친 뒤 API-014로 다시 검색한다.
import type { Criteria } from "../api/client";

export type ChipField = "work_ids" | "person_ids" | "genres" | "gus" | "years" | "travel";

export function withoutField(c: Criteria, field: ChipField): Criteria {
  switch (field) {
    case "travel":
      return { ...c, base_kind: null, station_id: null, location_id: null, point: null, travel_mode: null, travel_min: null };
    case "years":
      return { ...c, year_from: null, year_to: null };
    default:
      return { ...c, [field]: null };
  }
}

// 후보 선택: field는 work_ids·person_ids·gus·travel(역) 중 하나, value는 표준 ID
export function withChoice(c: Criteria, field: string, value: string): Criteria {
  if (field === "work_ids" || field === "person_ids") {
    const prev = (c[field] ?? []) as number[];
    return { ...c, [field]: [...new Set([...prev, Number(value)])] };
  }
  if (field === "gus") return { ...c, gus: [...new Set([...(c.gus ?? []), value])] };
  if (field === "travel") return { ...c, base_kind: "station", station_id: value, travel_mode: c.travel_mode ?? "walk", travel_min: c.travel_min ?? 10 };
  return c;
}

export const EMPTY: Criteria = { result_type: "LOCATION" };
