"""MapService(COMP-04): 근접·필터 검색(API-005), 촬영지 상세(API-006), 선택 목록(API-007)."""

from dataclasses import dataclass
from typing import Literal

from app.data.models import Conditions, Location, LocationHit, Photo, Point, Station, WorkBrief
from app.data.repositories.location import LocationRepository
from app.data.repositories.station import StationRepository
from app.data.repositories.work import WorkRepository
from app.pipeline.certify import cert_block_reason

RADII_M = (500, 1000, 3000)  # FR-203
CARD_WORKS = 3  # FR-206
# 부산 16개 구·군(BR-15)
DISTRICTS = (
    "중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구",
    "해운대구", "사하구", "금정구", "강서구", "연제구", "수영구", "사상구", "기장군",
)  # fmt: skip
# 부산 밖 좌표는 받지 않는다(ERR-001). 대략의 경계 상자
BUSAN_BOUNDS = (34.85, 35.45, 128.75, 129.35)
DEFAULT_STATION = "113"  # 부산역(FR-201)
COORD_SOURCE = "DATA-06"
STATION_SOURCE = "DATA-08"


class NotFound(Exception):
    pass


class InvalidInput(ValueError):
    pass


@dataclass(frozen=True)
class MapFilters:
    genres: list[str] | None = None
    year_from: int | None = None
    year_to: int | None = None
    gus: list[str] | None = None


@dataclass(frozen=True)
class Base:
    kind: Literal["point", "station", "gu"]
    point: Point | None = None
    station_id: str | None = None
    gu: str | None = None


@dataclass(frozen=True)
class MapItem:
    id: int
    name: str
    lat: float
    lon: float
    distance_m: float | None
    works: list[WorkBrief]
    work_count: int
    station: Station | None


@dataclass(frozen=True)
class MapResult:
    items: list[MapItem]
    source_ids: list[str]


@dataclass(frozen=True)
class LocationDetail:
    location: Location
    photo: Photo | None
    station: Station | None
    works: list[WorkBrief]
    certifiable: bool
    cert_block_reason: str | None
    source_ids: list[str]


def in_busan(p: Point) -> bool:
    lat_lo, lat_hi, lon_lo, lon_hi = BUSAN_BOUNDS
    return lat_lo <= p.lat <= lat_hi and lon_lo <= p.lon <= lon_hi


class MapService:
    def __init__(self, locations: LocationRepository, stations: StationRepository, works: WorkRepository):
        self.locations = locations
        self.stations = stations
        self.works = works

    async def search(self, base: Base, radius_m: int, filters: MapFilters) -> MapResult:
        if radius_m not in RADII_M:
            raise InvalidInput("radius_m")
        if filters.gus and not set(filters.gus) <= set(DISTRICTS):
            raise InvalidInput("gus")
        cond = Conditions(genres=filters.genres, year_from=filters.year_from, year_to=filters.year_to, gus=filters.gus)
        hits = await self._hits(base, radius_m, cond)
        hits = [h for h in hits if h.lat is not None]  # FR-210
        by_loc = await self.works.by_locations([h.id for h in hits])
        stations = {s.id: s for s in await self.stations.all()}
        items = [
            MapItem(
                id=h.id, name=h.name, lat=h.lat, lon=h.lon, distance_m=h.dist_m,
                works=by_loc[h.id][:CARD_WORKS], work_count=len(by_loc[h.id]),
                station=stations.get(h.nearest_station_id),
            )
            for h in hits
        ]  # fmt: skip
        sources = {sid for h in hits for sid in h.source_ids}
        if items:
            sources.add(COORD_SOURCE)
        if any(i.station for i in items):
            sources.add(STATION_SOURCE)
        return MapResult(items=items, source_ids=sorted(sources))

    async def _hits(self, base: Base, radius_m: int, cond: Conditions) -> list[LocationHit]:
        if base.kind == "gu":
            if base.gu not in DISTRICTS:
                raise InvalidInput("base.gu")
            # 구·군 기준은 반경 대신 그 구·군 전체(FR-202). 일치 작품 수 순
            gus = [base.gu] if not cond.gus else [g for g in cond.gus if g == base.gu]
            if not gus:
                return []
            hits = await self.locations.search(Conditions(**{**cond.__dict__, "gus": gus}), limit=20)
            return list(hits)
        if base.kind == "station":
            station = await self.stations.get(base.station_id or "")
            if station is None:
                raise InvalidInput("base.station_id")
            point = Point(station.lat, station.lon)
        else:
            point = base.point
            if point is None or not in_busan(point):
                raise InvalidInput("base")
        return await self.locations.within_radius(point, radius_m, cond)

    async def get_location(self, location_id: int) -> LocationDetail:
        loc = await self.locations.get(location_id)
        if loc is None:
            raise NotFound(location_id)
        photo = await self.locations.photo(location_id)
        station = await self.stations.get(loc.nearest_station_id) if loc.nearest_station_id else None
        works = (await self.works.by_locations([location_id]))[location_id]
        shooting_sources = await self.locations.shooting_sources(location_id)
        sources = set(shooting_sources)
        if loc.lat is not None:
            sources.add(COORD_SOURCE)
        if station:
            sources.add(STATION_SOURCE)
        if photo:
            sources.add(photo.source_id)
        reason = cert_block_reason(loc)
        return LocationDetail(
            location=loc, photo=photo, station=station, works=works,
            certifiable=reason is None, cert_block_reason=reason, source_ids=sorted(sources),
        )  # fmt: skip

    async def meta(self) -> dict:
        return {
            "districts": list(DISTRICTS),
            "stations": await self.stations.all(),
            "genres": await self.works.genres(),
            "year_range": await self.works.year_range(),
            "default_station_id": DEFAULT_STATION,
        }
