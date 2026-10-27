"""StampService(COMP-07): 방문 인증(API-016), 토큰 확인(API-017), 완주 배지(API-018).

서버는 위치·스탬프를 저장하지 않는다(ADR-009). 좌표는 이 요청 안에서 판정에만 쓰고 버린다.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Literal

from app.data.models import Location, WorkBrief
from app.data.repositories.course import CourseRepository
from app.data.repositories.location import LocationRepository
from app.data.repositories.work import WorkRepository
from app.pipeline.certify import cert_block_reason
from app.services.stamp import geofence
from app.services.stamp.tokens import BadToken, TokenSigner

MAX_TOKENS = 500  # 한 번에 확인하는 토큰 수 상한
CUSTOM_MIN, CUSTOM_MAX = 2, 10  # 저장 코스의 장소 수(FR-304와 같은 범위)


class NotFound(Exception):
    pass


class InvalidInput(ValueError):
    pass


class NotCertifiable(Exception):
    """ERR-009. 이유(no_coords·excluded·private 등)를 담는다."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class CertifyResult:
    ok: bool
    token: str | None
    reason: Literal["accuracy", "distance", "duplicate"] | None
    distance_m: int


@dataclass(frozen=True)
class StampEntry:
    location: Location
    work: WorkBrief | None
    iat: int


@dataclass(frozen=True)
class BadgeEntry:
    course_key: str
    iat: int


@dataclass(frozen=True)
class VerifyResult:
    valid: list[StampEntry]
    invalid_count: int
    badges: list[BadgeEntry] = field(default_factory=list)


@dataclass(frozen=True)
class BadgeResult:
    ok: bool
    token: str | None
    course_key: str
    missing: list[int] = field(default_factory=list)


def custom_course_key(location_ids: list[int]) -> str:
    """저장 코스는 서버에 없으므로 장소 집합으로 키를 만든다. 순서는 상관없다."""
    digest = hashlib.sha256(",".join(map(str, sorted(set(location_ids)))).encode()).hexdigest()
    return f"custom:{digest[:16]}"


class StampService:
    def __init__(self, locations: LocationRepository, works: WorkRepository, courses: CourseRepository,
                 signer: TokenSigner):  # fmt: skip
        self.locations = locations
        self.works = works
        self.courses = courses
        self.signer = signer

    def _stamped_locations(self, tokens: list[str]) -> tuple[dict[int, int], int]:
        """유효한 스탬프 토큰의 {장소: 가장 이른 iat}와 무효 개수."""
        seen: dict[int, int] = {}
        invalid = 0
        for t in dict.fromkeys(tokens[:MAX_TOKENS]):
            try:
                c = self.signer.verify(t, "stamp")
            except BadToken:
                invalid += 1
                continue
            assert c.loc is not None
            seen[c.loc] = min(c.iat, seen.get(c.loc, c.iat))
        return seen, invalid

    async def certify(self, location_id: int, fix: geofence.GeoFix, held: list[str]) -> CertifyResult:
        loc = await self.locations.get(location_id)
        if loc is None:
            raise NotFound(location_id)
        reason = cert_block_reason(loc)
        if reason is not None:
            raise NotCertifiable(reason)
        assert loc.lat is not None and loc.lon is not None
        v = geofence.check(fix, loc.lat, loc.lon, loc.cert_radius_m)
        if not v.ok:
            return CertifyResult(False, None, v.reason, v.distance_m)
        stamped, _ = self._stamped_locations(held)
        if location_id in stamped:  # FR-505 같은 장소는 한 번만
            return CertifyResult(False, None, "duplicate", v.distance_m)
        return CertifyResult(True, self.signer.stamp(location_id), None, v.distance_m)

    async def verify(self, tokens: list[str], badge_tokens: list[str] | None = None) -> VerifyResult:
        stamped, invalid = self._stamped_locations(tokens)
        badges: dict[str, int] = {}
        for t in dict.fromkeys((badge_tokens or [])[:MAX_TOKENS]):
            try:
                c = self.signer.verify(t, "badge")
            except BadToken:
                invalid += 1
                continue
            assert c.course_key is not None
            badges[c.course_key] = min(c.iat, badges.get(c.course_key, c.iat))
        locs = {loc.id: loc for loc in await self.locations.many(list(stamped))}
        works = await self.works.by_locations(list(locs))
        # 지워진 촬영지의 토큰은 보여 줄 수 없으니 무효로 센다
        invalid += sum(1 for i in stamped if i not in locs)
        valid = [
            StampEntry(locs[i], (works.get(i) or [None])[0], iat)
            for i, iat in sorted(stamped.items(), key=lambda kv: kv[1])
            if i in locs
        ]
        return VerifyResult(valid, invalid, [BadgeEntry(k, iat) for k, iat in sorted(badges.items(), key=lambda kv: kv[1])])

    async def issue_badge(
        self, course_id: int | None, location_ids: list[int] | None, stamps: list[str]
    ) -> BadgeResult:
        if course_id is not None:
            course = await self.courses.get(course_id)
            if course is None or course.status != "approved":
                raise NotFound(course_id)
            targets = [s.location_id for s in course.stops]
            key = f"course:{course_id}"
        else:
            targets = list(dict.fromkeys(location_ids or []))
            if not CUSTOM_MIN <= len(targets) <= CUSTOM_MAX:
                raise InvalidInput(f"장소는 {CUSTOM_MIN}~{CUSTOM_MAX}곳")
            key = custom_course_key(targets)
        stamped, _ = self._stamped_locations(stamps)
        missing = [i for i in targets if i not in stamped]
        if missing:
            return BadgeResult(False, None, key, missing)
        return BadgeResult(True, self.signer.badge(key), key)
