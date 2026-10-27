"""QueryContext와 Criteria(COMP-06, SDD CD-03). 파이프라인 단계는 모두 QueryContext를 받아 고친 뒤 돌려준다."""

from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Literal

from app.data.ai_gateway.deadline import Deadline
from app.data.models import Point


class QueryStatus(StrEnum):
    OK = "OK"
    RELAXED = "RELAXED"
    NOT_FOUND = "NOT_FOUND"
    NEEDS_CHOICE = "NEEDS_CHOICE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    FALLBACK = "FALLBACK"


# 이 상태가 되면 이후 단계를 건너뛴다
STOP = {QueryStatus.NOT_FOUND, QueryStatus.NEEDS_CHOICE, QueryStatus.OUT_OF_SCOPE, QueryStatus.FALLBACK}

BaseKind = Literal["station", "any_station", "location", "point"]
TravelMode = Literal["walk", "subway"]


@dataclass(frozen=True)
class Criteria:
    """사전 대조를 마친 표준 조건. 필터 패널(API-014)도 이 모양을 그대로 보낸다.

    기준 위치(base)와 이동(travel):
    - station + walk N분 → 그 역 좌표에서 반경 / station + subway N분 → 도시철도 + 걷기(T3)
    - any_station + walk N분 → 아무 역에서 걸어서 N분(T3)
    - location·point + walk N분 → 그 지점에서 반경. travel이 없으면 반경 1km
    """

    work_ids: list[int] | None = None
    person_ids: list[int] | None = None
    genres: list[str] | None = None
    gus: list[str] | None = None
    year_from: int | None = None
    year_to: int | None = None
    base_kind: BaseKind | None = None
    station_id: str | None = None
    location_id: int | None = None
    point: Point | None = None
    travel_mode: TravelMode | None = None
    travel_min: int | None = None
    result_type: Literal["LOCATION", "WORK"] = "LOCATION"

    def without(self, name: str) -> "Criteria":
        """조건 하나를 뺀다. 칩 삭제(FR-412)와 조건 완화(FR-405)가 쓴다."""
        match name:
            case "travel":
                return replace(self, travel_mode=None, travel_min=None, base_kind=None, station_id=None,
                               location_id=None, point=None)  # fmt: skip
            case "years":
                return replace(self, year_from=None, year_to=None)
            case "genres" | "gus" | "work_ids" | "person_ids":
                return replace(self, **{name: None})
        raise ValueError(name)

    def is_empty(self) -> bool:
        return self == Criteria(result_type=self.result_type)


@dataclass(frozen=True)
class Chip:
    """해석한 조건 하나(FR-412). field는 Criteria.without()에 넘기는 이름."""

    field: str
    label: str


@dataclass(frozen=True)
class Choice:
    """같은 이름의 후보가 둘 이상일 때 고를 값(FR-403). value는 canonical ID."""

    field: str
    surface: str
    label: str
    value: str


@dataclass
class QueryContext:
    text: str
    here: Point | None = None  # 브라우저가 보낸 현재 위치. 저장·기록하지 않는다
    masked: str = ""
    masked_kinds: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)  # conditions.v1(이름 그대로)
    criteria: Criteria = field(default_factory=Criteria)
    labels: dict[str, str] = field(default_factory=dict)  # "person_ids:1" → "강도윤"
    chips: list[Chip] = field(default_factory=list)
    choices: list[Choice] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)  # 사전에 없어 뺀 조건 등(FR-403)
    results: list = field(default_factory=list)  # LocationHit 또는 WorkHit
    relaxed: list[str] = field(default_factory=list)
    summary: list[str] = field(default_factory=list)
    summary_dropped: int = 0
    evidence: dict | None = None
    status: QueryStatus = QueryStatus.OK
    deadline: Deadline | None = None
