"""API-005 근접·필터 검색, API-006 촬영지 상세, API-007 선택 목록."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.api.assembler import Assembler, SourceCardOut
from app.api.deps import get_assembler, get_map_service
from app.api.errors import AppError
from app.data.models import Point
from app.services.map.service import Base, InvalidInput, MapFilters, MapService, NotFound


class BaseIn(BaseModel):
    """기준 위치: 좌표, 역, 구·군 중 하나. 좌표는 요청 본문으로만 받고 저장·기록하지 않는다(NFR-003)."""

    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    station_id: str | None = Field(None, max_length=10)
    gu: str | None = Field(None, max_length=10)

    @model_validator(mode="after")
    def exactly_one(self):
        given = [self.lat is not None or self.lon is not None, self.station_id is not None, self.gu is not None]
        if sum(given) != 1 or ((self.lat is None) != (self.lon is None)):
            raise ValueError("base는 {lat, lon}, {station_id}, {gu} 중 하나")
        return self

    def to_base(self) -> Base:
        if self.station_id is not None:
            return Base("station", station_id=self.station_id)
        if self.gu is not None:
            return Base("gu", gu=self.gu)
        return Base("point", point=Point(self.lat, self.lon))


class FiltersIn(BaseModel):
    genres: list[str] | None = Field(None, max_length=10)
    year_from: int | None = Field(None, ge=1900, le=2100)
    year_to: int | None = Field(None, ge=1900, le=2100)
    gus: list[str] | None = Field(None, max_length=16)


class SearchIn(BaseModel):
    base: BaseIn
    radius_m: Literal[500, 1000, 3000] = 1000
    filters: FiltersIn = FiltersIn()


class WorkBriefOut(BaseModel):
    id: int
    title: str
    release_year: int | None


class StationOut(BaseModel):
    id: str
    name: str
    line: str
    lat: float
    lon: float
    gu: str


class MapItemOut(BaseModel):
    id: int
    name: str
    lat: float
    lon: float
    distance_m: float | None
    works: list[WorkBriefOut]
    work_count: int
    station: StationOut | None


class SearchOut(BaseModel):
    items: list[MapItemOut]
    source_ids: list[str]
    sources: list[SourceCardOut]


class PhotoOut(BaseModel):
    url: str
    title: str


class LocationOut(BaseModel):
    id: int
    name: str
    address: str | None
    gu: str | None
    lat: float | None
    lon: float | None


class LocationDetailOut(BaseModel):
    location: LocationOut
    photo: PhotoOut | None
    tags: list[str]
    station: StationOut | None
    walk_min: int | None
    works: list[WorkBriefOut]
    caution: str
    safety_note: str | None
    certifiable: bool
    cert_block_reason: str | None
    cert_radius_m: int
    source_ids: list[str]
    sources: list[SourceCardOut]


class MetaOut(BaseModel):
    districts: list[str]
    stations: list[StationOut]
    genres: list[str]
    year_range: tuple[int, int] | None
    default_station_id: str


router = APIRouter(tags=["지도"])


@router.post("/api/locations/search", response_model=SearchOut)
async def search_locations(
    body: SearchIn, svc: MapService = Depends(get_map_service), asm: Assembler = Depends(get_assembler)
):
    f = body.filters
    try:
        result = await svc.search(
            body.base.to_base(),
            body.radius_m,
            MapFilters(genres=f.genres or None, year_from=f.year_from, year_to=f.year_to, gus=f.gus or None),
        )
    except InvalidInput as e:
        raise AppError("ERR-001", f"입력 값을 확인해 주세요({e})") from None
    return SearchOut(
        items=[MapItemOut.model_validate(i, from_attributes=True) for i in result.items],
        source_ids=result.source_ids,
        sources=await asm.cards(result.source_ids),
    )


@router.get("/api/locations/{location_id}", response_model=LocationDetailOut)
async def get_location(
    location_id: int, svc: MapService = Depends(get_map_service), asm: Assembler = Depends(get_assembler)
):
    try:
        d = await svc.get_location(location_id)
    except NotFound:
        raise HTTPException(404, "촬영지를 찾을 수 없습니다") from None
    loc = d.location
    return LocationDetailOut(
        location=LocationOut.model_validate(loc, from_attributes=True),
        photo=PhotoOut.model_validate(d.photo, from_attributes=True) if d.photo else None,
        tags=loc.tags,
        station=StationOut.model_validate(d.station, from_attributes=True) if d.station else None,
        walk_min=loc.station_walk_min,
        works=[WorkBriefOut.model_validate(w, from_attributes=True) for w in d.works],
        caution=loc.caution,
        safety_note=loc.safety_note,
        certifiable=d.certifiable,
        cert_block_reason=d.cert_block_reason,
        cert_radius_m=loc.cert_radius_m,
        source_ids=d.source_ids,
        sources=await asm.cards(d.source_ids),
    )


@router.get("/api/meta", response_model=MetaOut)
async def meta(svc: MapService = Depends(get_map_service)):
    m = await svc.meta()
    return MetaOut(
        districts=m["districts"],
        stations=[StationOut.model_validate(s, from_attributes=True) for s in m["stations"]],
        genres=m["genres"],
        year_range=m["year_range"],
        default_station_id=m["default_station_id"],
    )
