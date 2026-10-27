"""Geofence(BR-07): 정확도 50m 이하이고 하버사인 거리가 인증 반경 이하일 때만 성공."""

from dataclasses import dataclass
from typing import Literal

from app.pipeline.travel import haversine_m

MAX_ACCURACY_M = 50
DEFAULT_RADIUS_M = 100


@dataclass(frozen=True)
class GeoFix:
    """요청 처리 중에만 존재한다. 저장소·로그로 넘기지 않는다."""

    lat: float
    lon: float
    accuracy_m: float


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: Literal["accuracy", "distance"] | None
    distance_m: int


def check(fix: GeoFix, lat: float, lon: float, radius_m: int | None) -> Verdict:
    d = haversine_m(fix.lat, fix.lon, lat, lon)
    shown = round(d)
    if fix.accuracy_m > MAX_ACCURACY_M:
        return Verdict(False, "accuracy", shown)
    # 부동소수 오차로 정확히 반경인 점이 떨어지지 않게 0.1m 단위로 비교한다(반경 포함)
    if round(d, 1) > (radius_m or DEFAULT_RADIUS_M):
        return Verdict(False, "distance", shown)
    return Verdict(True, None, shown)
