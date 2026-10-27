"""저장소 계층이 돌려주는 값 객체. 업무 계층은 이 타입만 알고 SQL은 모른다."""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

Policy = Literal["STORE", "ID_ONLY", "NO_STORE"]


@dataclass(frozen=True)
class Point:
    lat: float
    lon: float


@dataclass(frozen=True)
class Conditions:
    """검색 조건(conditions.v1을 DictionaryResolver가 ID로 바꾼 뒤, 또는 필터 패널 입력).

    '조건 없음'은 빈 목록이 아니라 None이다. 이동 조건은 셋 중 하나만 쓴다.
    - point + radius_m: 그 지점에서 반경(현재 위치·장소·특정 역에서 걸어서 N분, 지도 반경) → T2
    - any_station_walk_min: 아무 역에서 걸어서 N분 → T3
    - from_station + minutes: 그 역에서 도시철도 + 내려서 걷기 N분 → T3
    """

    work_ids: list[int] | None = None
    person_ids: list[int] | None = None
    genres: list[str] | None = None
    gus: list[str] | None = None
    year_from: int | None = None
    year_to: int | None = None
    point: Point | None = None
    radius_m: float | None = None
    any_station_walk_min: int | None = None
    from_station: str | None = None
    minutes: int | None = None
    result_type: Literal["LOCATION", "WORK"] = "LOCATION"


@dataclass(frozen=True)
class LocationHit:
    id: int
    name: str
    gu: str | None
    lat: float | None
    lon: float | None
    work_ids: list[int]
    source_ids: list[str]
    dist_m: float | None = None
    travel_min: float | None = None
    nearest_station_id: str | None = None


@dataclass(frozen=True)
class WorkHit:
    id: int
    title: str
    release_year: int | None
    genres: list[str]
    location_count: int
    source_ids: list[str]


@dataclass(frozen=True)
class Location:
    id: int
    name: str
    address: str | None
    gu: str | None
    lat: float | None
    lon: float | None
    tags: list[str]
    caution: str
    safety_note: str | None
    cert_radius_m: int
    cert_excluded: bool
    nearest_station_id: str | None
    station_walk_min: int | None


@dataclass(frozen=True)
class LocationAttrs:
    """관리자가 편집하는 촬영지 속성(API-023, FR-610). None인 항목은 바꾸지 않는다."""

    caution: str | None = None
    safety_note: str | None = None
    cert_radius_m: int | None = None
    cert_excluded: bool | None = None


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    line: str
    lat: float
    lon: float
    gu: str


@dataclass(frozen=True)
class Source:
    id: str
    org: str
    name: str
    url: str
    license: str
    policy: Policy
    base_date: date | None = None


@dataclass(frozen=True)
class SourceCard:
    """화면 출처 카드: 제공기관·데이터명·기준일·원문 링크(FR-704)."""

    id: str
    org: str
    name: str
    base_date: date | None
    url: str


@dataclass(frozen=True)
class Page:
    items: list = field(default_factory=list)
    total: int = 0


@dataclass(frozen=True)
class Work:
    id: int
    title: str
    release_year: int | None
    genres: list[str]
    source_id: str
    kmdb_id: str | None = None
    kobis_movie_cd: str | None = None
    location_count: int = 0


@dataclass(frozen=True)
class WorkQuery:
    """작품 목록 조건(API-001). sort는 year·locations만."""

    q: str | None = None
    genre: str | None = None
    sort: Literal["year", "locations"] = "locations"
    page: int = 1


@dataclass(frozen=True)
class Person:
    id: int
    name: str
    role: str
    ord: int


@dataclass(frozen=True)
class WorkLocation:
    id: int
    name: str
    gu: str | None
    lat: float | None
    lon: float | None
    source_id: str


@dataclass(frozen=True)
class WorkDetail:
    work: Work
    people: list[Person]
    locations: list[WorkLocation]
    source_ids: list[str]
    kmdb: dict | None = None  # KMDb 정책이 STORE일 때만 채워짐(TBD-01)


@dataclass(frozen=True)
class MovieInfo:
    """KMDb 상세(저장본 또는 실시간). 이미지·예고편은 주소만 쓰고 파일은 저장하지 않는다."""

    source_id: str
    plot: str | None = None
    keywords: list[str] = field(default_factory=list)
    posters: list[str] = field(default_factory=list)
    stills: list[str] = field(default_factory=list)
    vods: list[dict] = field(default_factory=list)
    link: str | None = None


@dataclass(frozen=True)
class CourseStop:
    ord: int
    location_id: int
    dwell_min: int = 20
    leg_mode: str | None = None
    leg_min: int | None = None
    leg_line: str | None = None


@dataclass(frozen=True)
class Course:
    theme: Literal["work", "actor", "area"]
    title: str
    start_label: str
    start_lat: float
    start_lon: float
    total_min: int
    total_m: int
    stops: list[CourseStop] = field(default_factory=list)
    theme_ref: str | None = None
    status: Literal["draft", "approved"] = "draft"
    id: int | None = None


@dataclass(frozen=True)
class DictHit:
    kind: str
    surface: str
    canonical_id: str
    score: float


@dataclass(frozen=True)
class ReviewItem:
    id: int
    kind: str
    target_type: str
    target_id: int
    proposal: dict | None
    proposer: str | None
    model: str | None
    score: float | None
    status: str


@dataclass(frozen=True)
class SyncRun:
    id: int
    trigger: str
    status: str
    requested_by: str
    counts: dict | None = None
    prev_counts: dict | None = None
    failures: list | dict | None = None


@dataclass(frozen=True)
class WorkBrief:
    id: int
    title: str
    release_year: int | None


@dataclass(frozen=True)
class Photo:
    url: str
    title: str
    source_id: str
