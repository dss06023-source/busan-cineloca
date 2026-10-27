"""API-020 관리자 로그인, API-021 동기화 요청·리포트, API-022 검수 큐, API-023 촬영지 속성 편집, API-024 추천 코스."""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from app.api.admin_auth import COOKIE, SESSION_S, require_admin
from app.api.deps import get_pool
from app.api.errors import AppError
from app.data.models import LocationAttrs
from app.data.repositories import health as usage_repo
from app.services.admin.courses import AdminCourse, CourseAdmin
from app.services.admin.service import AdminService, Conflict, InvalidInput, NotFound

router = APIRouter(tags=["관리자"])
_PACIFIC = ZoneInfo("America/Los_Angeles")  # Gemini 하루 한도 기준(health와 같음)


def get_admin_service(request: Request) -> AdminService:
    return request.app.state.admin_service


class LoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=200)


@router.post("/api/admin/session", status_code=204, responses={401: {}, 423: {}})
async def login(body: LoginIn, request: Request, response: Response):
    token = request.app.state.admin_auth.login(body.password)
    response.set_cookie(COOKIE, token, max_age=SESSION_S, httponly=True, secure=True, samesite="strict",
                        path="/api/admin")  # fmt: skip
    response.status_code = 204
    return response


@router.delete("/api/admin/session", status_code=204)
async def logout(request: Request, response: Response):
    request.app.state.admin_auth.logout(request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE, path="/api/admin")
    response.status_code = 204
    return response


class SyncRunOut(BaseModel):
    id: int
    trigger: str
    status: str
    requested_by: str
    counts: dict | None
    prev_counts: dict | None
    guard: dict | None  # 건수 가드 결과(counts.guard). 위반이면 ok=false와 이유
    failures: list | dict | None


class SyncReportOut(BaseModel):
    runs: list[SyncRunOut]
    usage: dict[str, int]  # 오늘(태평양 시간) Gemini 호출 수(NFR-005)


class SyncRequestedOut(BaseModel):
    run_id: int


@router.post("/api/admin/sync", status_code=202, response_model=SyncRequestedOut)
async def request_sync(by: str = Depends(require_admin), svc: AdminService = Depends(get_admin_service)):
    return SyncRequestedOut(run_id=await svc.request_sync(by))


@router.get("/api/admin/sync", response_model=SyncReportOut)
async def sync_report(
    limit: int = Query(10, ge=1, le=50),
    _: str = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
    pool=Depends(get_pool),
):
    runs = await svc.sync_report(limit)
    usage = await usage_repo.usage_for(pool, datetime.now(_PACIFIC).date(), "gemini:")
    return SyncReportOut(
        runs=[
            SyncRunOut(
                **{
                    k: getattr(r, k)
                    for k in ("id", "trigger", "status", "requested_by", "counts", "prev_counts", "failures")
                },
                guard=(r.counts or {}).get("guard"),
            )  # fmt: skip
            for r in runs
        ],
        usage=usage,
    )


class ReviewOut(BaseModel):
    id: int
    kind: str
    target_type: str
    target_id: int
    target_label: str | None
    proposal: dict | None
    proposer: str | None
    model: str | None
    score: float | None
    status: str


class ReviewListOut(BaseModel):
    items: list[ReviewOut]


class DecideIn(BaseModel):
    id: int
    action: Literal["approve", "reject"]
    # 승인 전에 고친 값: 태그면 {tags: [...]}, 매칭이면 {kmdb_id}
    edit: dict | None = None


def _review(i, label=None) -> ReviewOut:
    return ReviewOut(**{k: getattr(i, k) for k in ReviewOut.model_fields if k != "target_label"}, target_label=label)


@router.get("/api/admin/reviews", response_model=ReviewListOut)
async def reviews(
    kind: Literal["tag", "match"] | None = Query(None),
    _: str = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    return ReviewListOut(items=[_review(p.item, p.label) for p in await svc.reviews_pending(kind)])


@router.patch("/api/admin/reviews", response_model=ReviewOut)
async def decide(body: DecideIn, by: str = Depends(require_admin), svc: AdminService = Depends(get_admin_service)):
    try:
        item = await svc.decide(body.id, body.action, by, body.edit)
    except NotFound:
        raise HTTPException(404, "처리할 검수 항목이 없습니다") from None
    except InvalidInput as e:
        raise AppError("ERR-001", f"입력 값을 확인해 주세요({e})") from None
    except Conflict as e:
        raise HTTPException(409, str(e)) from None
    return _review(item)


class LocationAttrsIn(BaseModel):
    caution: Literal["none", "private", "residential", "school"] | None = None
    safety_note: str | None = Field(None, max_length=200)
    cert_radius_m: int | None = Field(None, ge=50, le=300)
    cert_excluded: bool | None = None


class AdminLocationOut(BaseModel):
    id: int
    name: str
    caution: str
    safety_note: str | None
    cert_radius_m: int
    cert_excluded: bool
    tags: list[str]


@router.patch("/api/admin/locations/{location_id}", response_model=AdminLocationOut)
async def update_location(
    location_id: int,
    body: LocationAttrsIn,
    _: str = Depends(require_admin),
    svc: AdminService = Depends(get_admin_service),
):
    try:
        loc = await svc.update_location(location_id, LocationAttrs(**body.model_dump()))
    except NotFound:
        raise HTTPException(404, "촬영지를 찾을 수 없습니다") from None
    except InvalidInput as e:
        raise AppError("ERR-001", f"입력 값을 확인해 주세요({e})") from None
    return AdminLocationOut(**{k: getattr(loc, k) for k in AdminLocationOut.model_fields})


def get_course_admin(request: Request) -> CourseAdmin:
    return request.app.state.course_admin


class AdminStopOut(BaseModel):
    ord: int
    location_id: int
    name: str | None
    leg_mode: str | None  # 이전 지점(첫 장소는 출발지)에서 오는 구간
    leg_min: int | None
    leg_line: str | None


class AdminCourseOut(BaseModel):
    id: int
    theme: str
    theme_ref: str | None
    title: str
    status: str
    start_label: str
    total_min: int
    total_m: int
    stops: list[AdminStopOut]


class AdminCourseListOut(BaseModel):
    items: list[AdminCourseOut]


class CourseDraftIn(BaseModel):
    theme: Literal["work", "actor", "area"]
    ref: str = Field(min_length=1, max_length=20)  # 작품 id, 인물 id, 구·군 이름
    title: str | None = Field(None, max_length=60)


class CourseEditIn(BaseModel):
    id: int
    stops: list[int] | None = None  # 이 순서로 다시 계산하고 초안으로 돌린다
    title: str | None = Field(None, max_length=60)
    status: Literal["draft", "approved"] | None = None


def _course(a: AdminCourse) -> AdminCourseOut:
    c = a.course
    stops = [AdminStopOut(**s.__dict__, name=a.names.get(s.location_id)) for s in c.stops]
    fields = ("id", "theme", "theme_ref", "title", "status", "start_label", "total_min", "total_m")
    return AdminCourseOut(**{k: getattr(c, k) for k in fields}, stops=stops)


@router.get("/api/admin/courses", response_model=AdminCourseListOut)
async def courses(_: str = Depends(require_admin), svc: CourseAdmin = Depends(get_course_admin)):
    return AdminCourseListOut(items=[_course(a) for a in await svc.all()])


@router.post("/api/admin/courses", status_code=201, response_model=AdminCourseOut)
async def draft_course(body: CourseDraftIn, _: str = Depends(require_admin),
                       svc: CourseAdmin = Depends(get_course_admin)):  # fmt: skip
    try:
        return _course(await svc.draft_course(body.theme, body.ref, body.title))
    except NotFound:
        raise HTTPException(404, "작품이나 인물을 찾을 수 없습니다") from None
    except InvalidInput as e:
        raise AppError("ERR-001", f"입력 값을 확인해 주세요({e})") from None


@router.patch("/api/admin/courses", response_model=AdminCourseOut)
async def edit_course(body: CourseEditIn, by: str = Depends(require_admin),
                      svc: CourseAdmin = Depends(get_course_admin)):  # fmt: skip
    try:
        return _course(await svc.update_course(body.id, by, body.stops, body.title, body.status))
    except NotFound:
        raise HTTPException(404, "코스를 찾을 수 없습니다") from None
    except InvalidInput as e:
        raise AppError("ERR-001", f"입력 값을 확인해 주세요({e})") from None
