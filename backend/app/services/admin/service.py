"""AdminService(COMP-14): 검수 큐(API-022), 촬영지 속성 편집(API-023), 동기화 요청·리포트(API-021).

AI·규칙 제안은 review_item에 'pending'으로만 들어가고, 관리자가 승인해야 서비스 데이터에 반영된다(BR-04).
"""

from dataclasses import dataclass
from typing import Literal

from psycopg.errors import UniqueViolation

from app.data.models import Location, LocationAttrs, ReviewItem, SyncRun
from app.data.repositories.location import LocationRepository
from app.data.repositories.review import ReviewRepository
from app.data.repositories.sync import SyncRepository
from app.data.repositories.work import WorkRepository

CAUTIONS = ("none", "private", "residential", "school")
RADIUS_RANGE = (50, 300)  # BR-07
MAX_TAGS, MAX_TAG_LEN = 10, 20


class NotFound(Exception):
    pass


class InvalidInput(ValueError):
    pass


class Conflict(Exception):
    pass


@dataclass(frozen=True)
class PendingItem:
    item: ReviewItem
    label: str | None


def _clean_tags(raw: object) -> list[str]:
    if not isinstance(raw, list) or not raw:
        raise InvalidInput("tags는 비어 있지 않은 목록")
    tags = list(dict.fromkeys(t.strip() for t in raw if isinstance(t, str) and t.strip()))
    if not tags or len(tags) > MAX_TAGS or any(len(t) > MAX_TAG_LEN for t in tags):
        raise InvalidInput(f"태그는 1~{MAX_TAGS}개, 각 {MAX_TAG_LEN}자 이내")
    return tags


class AdminService:
    def __init__(self, reviews: ReviewRepository, locations: LocationRepository, works: WorkRepository,
                 sync: SyncRepository):  # fmt: skip
        self.reviews = reviews
        self.locations = locations
        self.works = works
        self.sync = sync

    async def reviews_pending(self, kind: str | None = None) -> list[PendingItem]:
        return [PendingItem(i, label) for i, label in await self.reviews.pending_labeled(kind)]

    async def decide(self, item_id: int, action: Literal["approve", "reject"], by: str,
                     edit: dict | None = None) -> ReviewItem:  # fmt: skip
        """승인하면 제안(관리자가 고친 값이 있으면 그것)을 반영한다. 반영 값은 처리 전에 검증한다."""
        current = {i.id: i for i, _ in await self.reviews.pending_labeled()}.get(item_id)
        if current is None:
            raise NotFound(item_id)
        proposal = {**(current.proposal or {}), **(edit or {})}
        if action == "approve":
            if current.kind == "tag":
                proposal["tags"] = _clean_tags(proposal.get("tags"))
            elif not isinstance(proposal.get("kmdb_id"), str) or not proposal["kmdb_id"].strip():
                raise InvalidInput("kmdb_id가 필요합니다")
        decided = await self.reviews.decide(item_id, "approved" if action == "approve" else "rejected", by)
        if decided is None:  # 그사이 다른 관리자가 처리
            raise NotFound(item_id)
        if action == "approve":
            await self._apply(decided, proposal)
        return decided

    async def _apply(self, item: ReviewItem, proposal: dict) -> None:
        if item.kind == "tag" and item.target_type == "location":
            if await self.locations.add_tags(item.target_id, proposal["tags"]) is None:
                raise NotFound(item.target_id)
        elif item.kind == "match" and item.target_type == "work":
            try:
                if not await self.works.set_match(item.target_id, proposal["kmdb_id"].strip()):
                    raise NotFound(item.target_id)
            except UniqueViolation:
                raise Conflict("다른 작품에 이미 연결된 KMDb ID입니다") from None

    async def update_location(self, location_id: int, attrs: LocationAttrs) -> Location:
        if attrs.caution is not None and attrs.caution not in CAUTIONS:
            raise InvalidInput("caution")
        lo, hi = RADIUS_RANGE
        if attrs.cert_radius_m is not None and not lo <= attrs.cert_radius_m <= hi:
            raise InvalidInput(f"인증 반경은 {lo}~{hi}m")
        loc = await self.locations.update_attrs(location_id, attrs)
        if loc is None:
            raise NotFound(location_id)
        return loc

    async def request_sync(self, by: str) -> int:
        """배치가 1분 안에 sync_run 요청을 집어 간다(ADR-012). 이미 대기·실행 중이면 그 요청을 돌려준다."""
        for run in await self.sync.recent(10):
            if run.status in ("requested", "running"):
                return run.id
        return await self.sync.request(by)

    async def sync_report(self, limit: int = 10) -> list[SyncRun]:
        return await self.sync.recent(limit)
