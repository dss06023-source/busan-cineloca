"""API-001 작품 목록, API-002 작품 상세, API-003 KOBIS 관람등급, API-004 AI 작품 소개."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.api.assembler import Assembler, SourceCardOut
from app.api.deps import ai_guard, get_archive_service, get_assembler
from app.api.errors import AppError
from app.data.ai_gateway.deadline import Deadline
from app.data.models import WorkQuery
from app.services.archive.service import ArchiveService, NotFound

router = APIRouter(tags=["작품"])


class WorkOut(BaseModel):
    id: int
    title: str
    release_year: int | None
    genres: list[str]
    location_count: int


class WorkListOut(BaseModel):
    items: list[WorkOut]
    total: int
    page: int


class PersonOut(BaseModel):
    id: int
    name: str
    role: str


class WorkLocationOut(BaseModel):
    id: int
    name: str
    gu: str | None
    lat: float | None
    lon: float | None


class WorkBriefOut(BaseModel):
    id: int
    title: str
    release_year: int | None


class VodOut(BaseModel):
    title: str | None = None
    url: str


class ImagesOut(BaseModel):
    """이미지는 원본 주소만 넘기고 파일은 저장하지 않는다(NO_STORE)."""

    posters: list[str]
    stills: list[str]


class WorkDetailOut(BaseModel):
    work: WorkOut
    people: list[PersonOut]
    plot: str | None
    keywords: list[str]
    images: ImagesOut
    vod: list[VodOut]
    kmdb_link: str | None
    locations: list[WorkLocationOut]
    related: list[WorkBriefOut]
    source_ids: list[str]
    sources: list[SourceCardOut]


class RatingOut(BaseModel):
    rating: str | None
    source_ids: list[str]
    sources: list[SourceCardOut]


class IntroIn(BaseModel):
    spoiler: Literal["none", "partial"] = "none"


class IntroFallbackLocation(BaseModel):
    id: int
    name: str
    gu: str | None


class IntroFallbackOut(BaseModel):
    plot: str | None
    locations: list[IntroFallbackLocation]


class IntroOut(BaseModel):
    status: Literal["ok", "degraded"]
    sentences: list[str]
    ai_generated: bool
    degraded: bool
    fallback: IntroFallbackOut | None
    dropped_count: int
    source_ids: list[str]
    sources: list[SourceCardOut]


@router.get("/api/works", response_model=WorkListOut)
async def list_works(
    q: str | None = Query(None, max_length=50),
    genre: str | None = Query(None, max_length=20),
    sort: Literal["locations", "year"] = "locations",
    page: int = Query(1, ge=1, le=1000),
    svc: ArchiveService = Depends(get_archive_service),
):
    result = await svc.list_works(WorkQuery(q=q, genre=genre, sort=sort, page=page))
    return WorkListOut(
        items=[WorkOut.model_validate(w, from_attributes=True) for w in result.items], total=result.total, page=page
    )


def _not_found() -> HTTPException:
    return HTTPException(404, "작품을 찾을 수 없습니다")


@router.get("/api/works/{work_id}", response_model=WorkDetailOut)
async def get_work(
    work_id: int, svc: ArchiveService = Depends(get_archive_service), asm: Assembler = Depends(get_assembler)
):
    try:
        v = await svc.get_work(work_id)
    except NotFound:
        raise _not_found() from None
    d, info = v.detail, v.info
    return WorkDetailOut(
        work=WorkOut.model_validate(d.work, from_attributes=True),
        people=[PersonOut.model_validate(p, from_attributes=True) for p in d.people],
        plot=info.plot if info else None,
        keywords=info.keywords if info else [],
        images=ImagesOut(posters=info.posters if info else [], stills=info.stills if info else []),
        vod=[VodOut(**v) for v in info.vods] if info else [],
        kmdb_link=info.link if info else None,
        locations=[WorkLocationOut.model_validate(loc, from_attributes=True) for loc in _unique(d.locations)],
        related=[WorkBriefOut.model_validate(w, from_attributes=True) for w in v.related],
        source_ids=v.source_ids,
        sources=await asm.cards(v.source_ids),
    )


def _unique(locations):
    """같은 촬영지가 출처별로 여러 행이면 하나만."""
    seen, out = set(), []
    for loc in locations:
        if loc.id not in seen:
            seen.add(loc.id)
            out.append(loc)
    return out


@router.get("/api/works/{work_id}/rating", response_model=RatingOut)
async def get_rating(
    work_id: int, svc: ArchiveService = Depends(get_archive_service), asm: Assembler = Depends(get_assembler)
):
    try:
        rating, source_ids = await svc.get_rating(work_id)
    except NotFound:
        raise _not_found() from None
    return RatingOut(rating=rating, source_ids=source_ids, sources=await asm.cards(source_ids))


@router.post("/api/works/{work_id}/intro", response_model=IntroOut, dependencies=[Depends(ai_guard)])
async def get_intro(
    work_id: int,
    body: IntroIn,
    request: Request,
    svc: ArchiveService = Depends(get_archive_service),
    asm: Assembler = Depends(get_assembler),
):
    deadline = Deadline(request.app.state.llm.config.deadline_s)
    try:
        r = await svc.get_intro(work_id, body.spoiler, deadline)
    except NotFound:
        raise _not_found() from None
    except ValueError as e:
        raise AppError("ERR-001") from e
    return IntroOut(
        status=r.status,
        sentences=r.sentences,
        ai_generated=not r.degraded,
        degraded=r.degraded,
        fallback=IntroFallbackOut(**r.fallback) if r.fallback else None,
        dropped_count=r.dropped_count,
        source_ids=r.source_ids,
        sources=await asm.cards(r.source_ids),
    )
