"""API-009 추천 코스 목록, API-010 추천 코스 상세, API-011 나만의 코스 경로, API-012 AI 맞춤 코스."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, model_validator

from app.api.assembler import Assembler, SourceCardOut
from app.api.deps import ai_guard, get_assembler, get_course_service
from app.api.errors import AppError
from app.data.ai_gateway.deadline import Deadline
from app.data.models import Point
from app.services.course.service import CourseService, InvalidInput, NotFound, RouteView, Start

router = APIRouter(tags=["코스"])


class StartIn(BaseModel):
    """출발지: 도시철도역, 촬영지, 현재 위치 중 하나(FR-303). 좌표는 저장·기록하지 않는다."""

    station_id: str | None = Field(None, max_length=10)
    location_id: int | None = None
    lat: float | None = Field(None, ge=34.8, le=35.5)
    lon: float | None = Field(None, ge=128.7, le=129.4)

    @model_validator(mode="after")
    def exactly_one(self):
        given = [
            self.station_id is not None,
            self.location_id is not None,
            self.lat is not None or self.lon is not None,
        ]
        if sum(given) != 1 or (self.lat is None) != (self.lon is None):
            raise ValueError("start는 {station_id}, {location_id}, {lat, lon} 중 하나")
        return self

    def to_start(self) -> Start:
        if self.station_id is not None:
            return Start("station", station_id=self.station_id)
        if self.location_id is not None:
            return Start("location", location_id=self.location_id)
        return Start("point", point=Point(self.lat, self.lon))


class CourseOut(BaseModel):
    id: int
    theme: str
    title: str
    start_label: str
    stop_count: int
    total_min: int
    total_m: int


class CourseListOut(BaseModel):
    items: list[CourseOut]


class WorkBriefOut(BaseModel):
    id: int
    title: str
    release_year: int | None


class StartOut(BaseModel):
    label: str
    lat: float
    lon: float


class StopOut(BaseModel):
    ord: int
    location_id: int
    name: str
    gu: str | None
    lat: float
    lon: float
    dwell_min: int
    works: list[WorkBriefOut]


class LegOut(BaseModel):
    mode: Literal["walk", "subway"]
    minutes: int
    distance_m: int
    line: str | None


class RouteOut(BaseModel):
    start: StartOut
    stops: list[StopOut]
    legs: list[LegOut]
    total_min: int
    total_m: int
    source_ids: list[str]
    sources: list[SourceCardOut]


class CourseDetailOut(BaseModel):
    course: CourseOut
    route: RouteOut


class PlanIn(BaseModel):
    start: StartIn
    location_ids: list[int] = Field(min_length=2, max_length=10)
    fixed_order: bool = False  # FR-305: 사용자가 바꾼 순서로 다시 계산


class ManualIn(BaseModel):
    """AI 장애 때 직접 고르는 조건(FR-312). preference.v1과 같은 이름."""

    genres: list[str] = Field(default_factory=list, max_length=10)
    mood_tags: list[str] = Field(default_factory=list, max_length=10)
    districts: list[str] = Field(default_factory=list, max_length=16)
    avoid: list[str] = Field(default_factory=list, max_length=5)


class AICourseIn(BaseModel):
    preference: str | None = Field(None, min_length=1, max_length=200)  # FR-307
    manual: ManualIn | None = None
    start: StartIn | None = None
    budget_h: float | None = Field(None, ge=1, le=8)

    @model_validator(mode="after")
    def one_of(self):
        if (self.preference is None) == (self.manual is None):
            raise ValueError("preference와 manual 중 하나")
        return self


class PreferenceOut(BaseModel):
    genres: list[str] = []
    mood_tags: list[str] = []
    work_ids: list[int] = []
    person_ids: list[int] = []
    gus: list[str] = []
    avoid: list[str] = []
    start: str | None = None
    budget_h: float | None = None


class ReasonOut(BaseModel):
    location_id: int
    text: str


class CourseIntroOut(BaseModel):
    title: str
    sentences: list[str]
    ai_generated: bool
    dropped_count: int


class OptionsOut(BaseModel):
    genres: list[str]
    mood_tags: list[str]
    districts: list[str]


class AICourseOut(BaseModel):
    status: Literal["OK", "FALLBACK", "OUT_OF_SCOPE", "INFEASIBLE"]
    preference: PreferenceOut | None
    route: RouteOut | None
    reasons: list[ReasonOut]
    intro: CourseIntroOut | None
    masked: bool
    notices: list[str]
    reason: Literal["budget", "candidates"] | None
    options: OptionsOut | None


def _course(c, stops: int) -> CourseOut:
    return CourseOut(id=c.id, theme=c.theme, title=c.title, start_label=c.start_label, stop_count=stops,
                     total_min=c.total_min, total_m=c.total_m)  # fmt: skip


async def _route(v: RouteView, asm: Assembler) -> RouteOut:
    r = v.route
    return RouteOut(
        start=StartOut(label=r.start.name, lat=r.start.lat, lon=r.start.lon),
        stops=[
            StopOut(
                ord=i + 1,
                location_id=p.id,
                name=p.name,
                gu=v.gus.get(p.id),
                lat=p.lat,
                lon=p.lon,
                dwell_min=r.dwell_min,
                works=[WorkBriefOut.model_validate(w, from_attributes=True) for w in v.works.get(p.id, [])[:3]],
            )
            for i, p in enumerate(r.stops)
        ],  # fmt: skip
        legs=[LegOut(mode=leg.mode, minutes=leg.minutes, distance_m=leg.distance_m, line=leg.line) for leg in r.legs],
        total_min=r.total_min,
        total_m=r.total_m,
        source_ids=v.source_ids,
        sources=await asm.cards(v.source_ids),
    )


@router.get("/api/courses", response_model=CourseListOut)
async def list_courses(
    theme: Literal["work", "actor", "area"] | None = Query(None), svc: CourseService = Depends(get_course_service)
):
    return CourseListOut(items=[_course(c, n) for c, n in await svc.list_recommended(theme)])


@router.get("/api/courses/{course_id}", response_model=CourseDetailOut)
async def get_course(
    course_id: int, svc: CourseService = Depends(get_course_service), asm: Assembler = Depends(get_assembler)
):
    try:
        c, view = await svc.get_course(course_id)
    except NotFound:
        raise HTTPException(404, "코스를 찾을 수 없습니다") from None
    return CourseDetailOut(course=_course(c, len(c.stops)), route=await _route(view, asm))


@router.post("/api/courses/plan", response_model=RouteOut)
async def plan_course(
    body: PlanIn, svc: CourseService = Depends(get_course_service), asm: Assembler = Depends(get_assembler)
):
    try:
        view = await svc.plan_custom(body.start.to_start(), body.location_ids, body.fixed_order)
    except InvalidInput as e:
        raise AppError("ERR-001", f"입력 값을 확인해 주세요({e})") from None
    return await _route(view, asm)


@router.post("/api/courses/ai", response_model=AICourseOut, dependencies=[Depends(ai_guard)])
async def ai_course(
    body: AICourseIn,
    request: Request,
    svc: CourseService = Depends(get_course_service),
    asm: Assembler = Depends(get_assembler),
):
    deadline = Deadline(request.app.state.llm.config.deadline_s)
    manual = None
    if body.manual:
        manual = {**body.manual.model_dump(), "out_of_scope": False}
    try:
        r = await svc.plan_ai(
            deadline, body.preference, manual, body.start.to_start() if body.start else None, body.budget_h
        )
    except InvalidInput as e:
        raise AppError("ERR-001", f"입력 값을 확인해 주세요({e})") from None
    return AICourseOut(
        status=r.status,
        preference=PreferenceOut(**r.preference) if r.preference else None,
        route=await _route(r.view, asm) if r.view else None,
        reasons=[ReasonOut(**x) for x in r.reasons],
        intro=CourseIntroOut(title=r.title, sentences=r.intro, ai_generated=r.intro_ai, dropped_count=r.dropped_count)
        if r.view
        else None,
        masked=r.masked,
        notices=r.notices,
        reason=r.reason,
        options=OptionsOut(**r.options) if r.options else None,
    )
