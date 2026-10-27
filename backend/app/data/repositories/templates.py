"""SearchTemplates T1~T4(build-plan 7장). SQL 파일은 앱 시작 때 한 번 읽어 상수로 둔다(ADR-010).

값은 모두 바인딩 매개변수로 넣고, 정렬은 템플릿에 고정, 결과 수는 1~MAX_LIMIT만 받는다.
"""

from pathlib import Path

from app.data.models import Conditions

_DIR = Path(__file__).parent / "sql"
_MATCHED = (_DIR / "_matched.sql").read_text(encoding="utf-8")

T1_FILTER, T2_NEAR_POINT, T3_NEAR_STATION, T4_WORKS = (
    (_DIR / f"{name}.sql").read_text(encoding="utf-8").replace("{matched}", _MATCHED)
    for name in ("t1_filter", "t2_near_point", "t3_near_station", "t4_works")
)

MAX_LIMIT = 20  # 검색 결과(API-013·014)
MAP_MAX_LIMIT = 300  # 지도 마커(API-005, 묶음 마커로 그림)
WALK_M_PER_MIN = 4000 / 60  # 시속 4km
DETOUR = 1.3  # 직선거리 보정(build-plan 5장 TravelTimeEstimator)


def walk_radius_m(minutes: int) -> float:
    """걸어서 N분 → 직선 반경(m) = N × 4000/60 ÷ 1.3"""
    return minutes * WALK_M_PER_MIN / DETOUR


def _none_if_empty(values):
    return list(values) if values else None


def choose(cond: Conditions, limit: int = MAX_LIMIT, max_limit: int = MAX_LIMIT) -> tuple[str, dict]:
    """조건에 맞는 템플릿 하나와 매개변수를 고른다."""
    if max_limit not in (MAX_LIMIT, MAP_MAX_LIMIT) or not 1 <= limit <= max_limit:
        raise ValueError(f"limit은 1~{max_limit}")
    params = {
        "work_ids": _none_if_empty(cond.work_ids),
        "person_ids": _none_if_empty(cond.person_ids),
        "genres": _none_if_empty(cond.genres),
        "gus": _none_if_empty(cond.gus),
        "year_from": cond.year_from,
        "year_to": cond.year_to,
        "limit": limit,
    }
    if cond.result_type == "WORK":
        return T4_WORKS, params
    if cond.point is not None:
        if cond.radius_m is None or cond.radius_m <= 0:
            raise ValueError("point에는 radius_m이 필요합니다")
        return T2_NEAR_POINT, {**params, "lat": cond.point.lat, "lon": cond.point.lon, "radius_m": cond.radius_m}
    if cond.any_station_walk_min is not None:
        return T3_NEAR_STATION, {**params, "base_station": None, "minutes": cond.any_station_walk_min}
    if cond.from_station is not None:
        if cond.minutes is None:
            raise ValueError("from_station에는 minutes가 필요합니다")
        return T3_NEAR_STATION, {**params, "base_station": cond.from_station, "minutes": cond.minutes}
    return T1_FILTER, params
