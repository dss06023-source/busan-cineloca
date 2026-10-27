"""API-013 AI 대화형 탐색, API-014 필터 패널 검색, API-015 새 대화."""

from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app.api.assembler import Assembler, SourceCardOut
from app.api.deps import ai_guard, get_assembler, get_query_service, session_id
from app.api.errors import AppError
from app.data.models import LocationHit, Point
from app.pipeline.query.context import Criteria
from app.services.query.service import QueryResult, QueryService

router = APIRouter(tags=["AI 탐색"])


class PointIO(BaseModel):
    lat: float = Field(ge=34.8, le=35.5)
    lon: float = Field(ge=128.7, le=129.4)


class CriteriaIO(BaseModel):
    """해석한 조건(칩)과 필터 패널 입력의 공통 모양."""

    work_ids: list[int] | None = Field(None, max_length=3)
    person_ids: list[int] | None = Field(None, max_length=3)
    genres: list[str] | None = Field(None, max_length=10)
    gus: list[str] | None = Field(None, max_length=16)
    year_from: int | None = Field(None, ge=1900, le=2100)
    year_to: int | None = Field(None, ge=1900, le=2100)
    base_kind: Literal["station", "any_station", "location", "point"] | None = None
    station_id: str | None = Field(None, max_length=10)
    location_id: int | None = None
    point: PointIO | None = None
    travel_mode: Literal["walk", "subway"] | None = None
    travel_min: int | None = Field(None, ge=1, le=60)
    result_type: Literal["LOCATION", "WORK"] = "LOCATION"

    def to_criteria(self) -> Criteria:
        data = self.model_dump(exclude={"point"})
        return Criteria(**data, point=Point(self.point.lat, self.point.lon) if self.point else None)

    @classmethod
    def of(cls, c: Criteria | None) -> "CriteriaIO | None":
        if c is None:
            return None
        data = {k: getattr(c, k) for k in cls.model_fields if k != "point"}
        return cls(**data, point=PointIO(lat=c.point.lat, lon=c.point.lon) if c.point else None)


class AskIn(BaseModel):
    text: str = Field(min_length=1, max_length=200)  # FR-401
    here: PointIO | None = None  # 현재 위치 기준일 때만. 저장·기록하지 않는다(NFR-003)


class FilterSearchIn(BaseModel):
    criteria: CriteriaIO
    labels: dict[str, str] = Field(default_factory=dict, max_length=20)


class ChipOut(BaseModel):
    field: Literal["work_ids", "person_ids", "genres", "gus", "years", "travel"]
    label: str


class ChoiceOut(BaseModel):
    field: str
    surface: str
    label: str
    value: str


class ResultWorkOut(BaseModel):
    id: int
    title: str
    release_year: int | None


class LocationItemOut(BaseModel):
    id: int
    name: str
    gu: str | None
    lat: float | None
    lon: float | None
    distance_m: float | None
    travel_min: float | None
    works: list[ResultWorkOut]


class WorkItemOut(BaseModel):
    id: int
    title: str
    release_year: int | None
    genres: list[str]
    location_count: int


class SummaryOut(BaseModel):
    sentences: list[str]
    ai_generated: bool
    dropped_count: int


class QueryOut(BaseModel):
    status: Literal["OK", "RELAXED", "NOT_FOUND", "NEEDS_CHOICE", "OUT_OF_SCOPE", "FALLBACK"]
    chips: list[ChipOut]
    choices: list[ChoiceOut]
    notices: list[str]
    criteria: CriteriaIO | None
    labels: dict[str, str]
    items: list[LocationItemOut]
    works: list[WorkItemOut]
    summary: SummaryOut | None
    relaxed: list[Literal["travel", "years", "genres", "gus"]]
    masked: bool
    prefill: CriteriaIO | None
    source_ids: list[str]
    sources: list[SourceCardOut]


async def _out(r: QueryResult, svc: QueryService, asm: Assembler) -> QueryOut:
    ctx = r.ctx
    locs = [h for h in ctx.results if isinstance(h, LocationHit)]
    works_by = await svc.works_by_locations([h.id for h in locs]) if locs else {}
    has_criteria = r.status.value not in ("FALLBACK", "OUT_OF_SCOPE")
    return QueryOut(
        status=r.status.value,
        chips=[ChipOut(field=c.field, label=c.label) for c in ctx.chips],
        choices=[ChoiceOut(**c.__dict__) for c in ctx.choices],
        notices=ctx.notices,
        criteria=CriteriaIO.of(ctx.criteria) if has_criteria else None,
        labels=ctx.labels,
        items=[
            LocationItemOut(
                id=h.id,
                name=h.name,
                gu=h.gu,
                lat=h.lat,
                lon=h.lon,
                distance_m=h.dist_m,
                travel_min=h.travel_min,
                works=[ResultWorkOut.model_validate(w, from_attributes=True) for w in works_by.get(h.id, [])[:3]],
            )
            for h in locs
        ],  # fmt: skip
        works=[
            WorkItemOut.model_validate(w, from_attributes=True) for w in ctx.results if not isinstance(w, LocationHit)
        ],
        summary=SummaryOut(sentences=ctx.summary, ai_generated=True, dropped_count=ctx.summary_dropped)
        if ctx.summary
        else None,
        relaxed=ctx.relaxed,
        masked=bool(ctx.masked_kinds),
        prefill=CriteriaIO.of(r.prefill),
        source_ids=r.source_ids,
        sources=await asm.cards(r.source_ids),
    )


@router.post("/api/query", response_model=QueryOut, dependencies=[Depends(ai_guard)])
async def ask(
    body: AskIn,
    sid: str | None = Depends(session_id),
    svc: QueryService = Depends(get_query_service),
    asm: Assembler = Depends(get_assembler),
):
    here = Point(body.here.lat, body.here.lon) if body.here else None
    return await _out(await svc.ask(sid, body.text, here), svc, asm)


@router.post("/api/search", response_model=QueryOut)
async def search(
    body: FilterSearchIn, svc: QueryService = Depends(get_query_service), asm: Assembler = Depends(get_assembler)
):
    c = body.criteria
    if (c.travel_mode is None) != (c.travel_min is None) or (c.base_kind == "point") != (c.point is not None):
        raise AppError("ERR-001", "이동 조건이나 기준 위치를 확인해 주세요")
    if c.base_kind == "station" and not c.station_id or c.base_kind == "location" and c.location_id is None:
        raise AppError("ERR-001", "기준 위치를 확인해 주세요")
    return await _out(await svc.search(c.to_criteria(), body.labels), svc, asm)


@router.delete("/api/query/session", status_code=204)
async def reset(request: Request, svc: QueryService = Depends(get_query_service)):
    if request.state.session_id:
        svc.reset(request.state.session_id)
    return Response(status_code=204)
