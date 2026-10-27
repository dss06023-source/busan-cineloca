"""API-016 방문 인증, API-017 토큰 확인, API-018 완주 배지. AI를 쓰지 않는다.

좌표는 판정에만 쓰고 응답·로그·DB에 남기지 않는다(ADR-009, NFR-003).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.api.errors import AppError
from app.api.routers.courses import WorkBriefOut
from app.services.stamp import geofence
from app.services.stamp.service import MAX_TOKENS, InvalidInput, NotCertifiable, NotFound, StampService

router = APIRouter(tags=["방문 인증"])

Token = Annotated[str, StringConstraints(max_length=1024)]


def get_stamp_service(request: Request) -> StampService:
    return request.app.state.stamp_service


class CertifyIn(BaseModel):
    location_id: int
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0)
    held: list[Token] = Field(default_factory=list, max_length=MAX_TOKENS)


class CertifyOut(BaseModel):
    ok: bool
    token: str | None
    reason: Literal["accuracy", "distance", "duplicate"] | None
    distance_m: int


class VerifyIn(BaseModel):
    tokens: list[Token] = Field(max_length=MAX_TOKENS)


class StampLocationOut(BaseModel):
    id: int
    name: str
    gu: str | None


class StampOut(BaseModel):
    location: StampLocationOut
    work: WorkBriefOut | None
    iat: int


class VerifyOut(BaseModel):
    valid: list[StampOut]
    invalid_count: int


class BadgeCourseIn(BaseModel):
    """추천 코스는 {id}, 브라우저에 저장한 코스는 {location_ids}(SD-04)."""

    id: int | None = None
    location_ids: list[int] | None = Field(None, max_length=10)

    @model_validator(mode="after")
    def one_of(self):
        if (self.id is None) == (self.location_ids is None):
            raise ValueError("course는 {id}와 {location_ids} 중 하나")
        return self


class BadgeIn(BaseModel):
    course: BadgeCourseIn
    stamps: list[Token] = Field(max_length=MAX_TOKENS)


class BadgeOut(BaseModel):
    ok: bool
    token: str | None
    course_key: str
    missing: list[int]


@router.post("/api/stamps", response_model=CertifyOut)
async def certify(body: CertifyIn, svc: StampService = Depends(get_stamp_service)):
    fix = geofence.GeoFix(body.lat, body.lon, body.accuracy_m)
    try:
        r = await svc.certify(body.location_id, fix, body.held)
    except NotFound:
        raise HTTPException(404, "촬영지를 찾을 수 없습니다") from None
    except NotCertifiable as e:
        raise AppError("ERR-009", detail=[{"reason": e.reason}]) from None
    return CertifyOut(ok=r.ok, token=r.token, reason=r.reason, distance_m=r.distance_m)


@router.post("/api/stamps/verify", response_model=VerifyOut)
async def verify(body: VerifyIn, svc: StampService = Depends(get_stamp_service)):
    r = await svc.verify(body.tokens)
    return VerifyOut(
        valid=[
            StampOut(
                location=StampLocationOut(id=e.location.id, name=e.location.name, gu=e.location.gu),
                work=WorkBriefOut(**vars(e.work)) if e.work else None,
                iat=e.iat,
            )
            for e in r.valid
        ],
        invalid_count=r.invalid_count,
    )


@router.post("/api/badges", response_model=BadgeOut)
async def badge(body: BadgeIn, svc: StampService = Depends(get_stamp_service)):
    try:
        r = await svc.issue_badge(body.course.id, body.course.location_ids, body.stamps)
    except NotFound:
        raise HTTPException(404, "코스를 찾을 수 없습니다") from None
    except InvalidInput as e:
        raise AppError("ERR-001", f"입력 값을 확인해 주세요({e})") from None
    return BadgeOut(ok=r.ok, token=r.token, course_key=r.course_key, missing=r.missing)
