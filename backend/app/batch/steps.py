"""동기화 단계(IngestStep): 수집(CollectStep) → 주소 좌표(GeocodeStep) → KMDb 매칭(MatchWorksStep).

최근접 역 단계는 역 좌표 원본이 생기면 더한다.
"""

import re
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import date
from typing import Protocol

from app.batch.job import SyncContext
from app.data.adapters.busan import FilmLocation
from app.data.adapters.errors import AdapterError, QuotaExhausted
from app.data.adapters.juso import GeoPoint
from app.data.adapters.kmdb_csv import SOURCE_ID as KMDB_SOURCE
from app.data.adapters.kmdb_csv import KmdbMovie, stored_kmdb
from app.data.adapters.policy import PolicyGuard
from app.data.models import StagedLocation, StagedShooting, StagedWork
from app.data.text import normalize
from app.pipeline.match import WorkMatcher

# 부산 16개 구·군. 주소에서 처음 나오는 것을 쓴다('부산 동구 … 동구 중앙대로'처럼 두 번 나와도 같다)
GU = ("중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구", "해운대구", "사하구", "금정구",
      "강서구", "연제구", "수영구", "사상구", "기장군")  # fmt: skip
_GU = re.compile(r"(?<!\S)(" + "|".join(sorted(GU, key=len, reverse=True)) + r")(?=\s|$|,|\))")


def gu_of(address: str | None) -> str | None:
    m = _GU.search(address or "")
    return m.group(1) if m else None


def work_key(title: str) -> str:
    return f"t:{normalize(title)}"


def location_key(name: str, gu: str | None) -> str:
    return f"{normalize(name)}|{gu or ''}"


class FilmLocationSource(Protocol):
    source_id: str

    async def fetch_all(self) -> list[FilmLocation]: ...


class CollectStep:
    """부산 원본(DATA-01 영화 속 부산정보, DATA-02 씨네맵)을 모아 작품·촬영지·촬영 관계로 만든다.

    작품은 정규화한 제목, 촬영지는 정규화한 장소명 + 구·군으로 합친다. 주소가 없는 레코드(DATA-01)는
    같은 이름의 장소가 다른 원본에 주소와 함께 한 곳만 있으면 그 주소를 쓴다. 좌표는 다음 단계(주소 좌표)가 채운다.
    """

    name = "collect"

    def __init__(self, sources: list[FilmLocationSource], today: Callable[[], date] = date.today):
        self.sources, self.today = sources, today

    async def run(self, ctx: SyncContext) -> None:
        records = [r for src in self.sources for r in await src.fetch_all()]
        # 장소명 → 주소가 있는 레코드의 주소들(같은 이름이 여러 구에 있으면 정하지 않는다)
        addr_by_name: dict[str, set[str]] = {}
        for r in records:
            if r.address and gu_of(r.address):
                addr_by_name.setdefault(normalize(r.place_name), set()).add(r.address)

        works: dict[str, StagedWork] = {}
        locs: dict[str, StagedLocation] = {}
        shoots: dict[tuple[str, str, str], StagedShooting] = {}
        base = self.today()
        for r in records:
            if not normalize(r.work_title) or not normalize(r.place_name):
                ctx.failures.append({"step": self.name, "error": "empty_title_or_place", "source": r.source_id})
                continue
            address = r.address
            if not address and len(found := addr_by_name.get(normalize(r.place_name), ())) == 1:
                address = next(iter(found))
            gu = gu_of(address)
            wk, lk = work_key(r.work_title), location_key(r.place_name, gu)
            year = int(r.release_date[:4]) if r.release_date and r.release_date[:4].isdigit() else None
            if (w := works.get(wk)) is None:
                works[wk] = StagedWork(wk, r.work_title, normalize(r.work_title), year, r.source_id)
            elif w.release_year is None and year:
                works[wk] = replace(w, release_year=year)
            if lk not in locs:
                locs[lk] = StagedLocation(lk, r.place_name, normalize(r.place_name), address, gu)
            raw = {k: v for k, v in (("work_title", r.work_title), ("place_name", r.place_name),
                                     ("address", r.address), ("release_date", r.release_date)) if v}  # fmt: skip
            shoots.setdefault((wk, lk, r.source_id), StagedShooting(wk, lk, r.source_id, raw, base))
        ctx.works, ctx.locations, ctx.shootings = list(works.values()), list(locs.values()), list(shoots.values())


class KmdbCatalog(Protocol):
    by_id: dict[str, KmdbMovie]

    def candidates(self, title: str, year: int | None = None, limit: int = 3) -> list[KmdbMovie]: ...


class MatchWorksStep:
    """작품마다 KMDb 후보를 찾아 BR-11로 판정한다. 자동 연결이면 kmdb_id와 저장본을 채우고,
    검수 범위면 match_candidate만 남겨 반영 때 검수 큐(review_item)로 보낸다."""

    name = "match_kmdb"

    def __init__(self, catalog: KmdbCatalog, policy: PolicyGuard,
                 reviewed: Callable[[], Awaitable[dict[str, str]]] | None = None,
                 matcher: WorkMatcher | None = None):  # fmt: skip
        self.catalog, self.policy, self.reviewed = catalog, policy, reviewed
        self.matcher = matcher or WorkMatcher()

    async def run(self, ctx: SyncContext) -> None:
        # 관리자가 검수로 연결한 작품은 다시 매칭하지 않고 그 ID로 저장본만 채운다
        reviewed = await self.reviewed() if self.reviewed else {}
        out = []
        for w in ctx.works:
            if kmdb_id := reviewed.get(w.ext_key) or w.kmdb_id:  # 검수 연결, 또는 출처가 이미 준 KMDb ID
                status, sc = (w.match_status, w.match_score) if w.match_status != "unmatched" else ("auto", 1.0)
                out.append(replace(w, kmdb_id=kmdb_id, kmdb=self._stored(kmdb_id), match_status=status, match_score=sc))
                continue
            r = self.matcher.decide(w.title, w.release_year, self.catalog.candidates(w.title, w.release_year))
            if r.status == "auto":
                w = replace(w, kmdb_id=r.kmdb_id, match_status="auto", match_score=r.score,
                            kmdb=self._stored(r.kmdb_id))  # fmt: skip
            else:
                w = replace(w, match_status="unmatched", match_score=r.score,
                            match_candidate=r.kmdb_id if r.status == "review" else None)  # fmt: skip
            out.append(w)
        ctx.works = out

    def _stored(self, kmdb_id: str | None) -> dict | None:
        # STORE일 때만 줄거리·키워드·링크를 싣는다(ID_ONLY면 kmdb_id만, TBD-01)
        m = self.catalog.by_id.get(kmdb_id) if kmdb_id else None
        return stored_kmdb(m) if m and self.policy.policies.get(KMDB_SOURCE) == "STORE" else None


class Geocoder(Protocol):
    async def geocode(self, address: str) -> GeoPoint | None: ...


class GeocodeStep:
    """주소가 있고 좌표가 없는 촬영지에 좌표를 채운다(DATA-06). 못 찾으면 geocode_status = failed로 두고
    관리자가 보정한다. 지난 반영에서 같은 주소로 찾은 좌표가 있으면 다시 부르지 않는다(하루 호출 한도).
    하루 한도에 닿으면 나머지는 failed로 두고 다음 동기화에 맡긴다."""

    name = "geocode"

    def __init__(self, geocoder: Geocoder,
                 known: Callable[[], Awaitable[dict[str, tuple[str, float, float]]]] | None = None):  # fmt: skip
        self.geocoder, self.known = geocoder, known

    async def run(self, ctx: SyncContext) -> None:
        known = await self.known() if self.known else {}
        errors: dict[str, int] = {}
        stopped = False
        out = []
        for loc in ctx.locations:
            if loc.lat is not None or not loc.address:
                out.append(loc)
                continue
            prev = known.get(loc.ext_key)
            if prev and prev[0] == loc.address:
                out.append(replace(loc, lat=prev[1], lon=prev[2], geocode_status="ok"))
                continue
            point = None
            if not stopped:
                try:
                    point = await self.geocoder.geocode(loc.address)
                except QuotaExhausted:
                    stopped = True
                    errors["QuotaExhausted"] = errors.get("QuotaExhausted", 0) + 1
                except AdapterError as e:  # 한 곳이 실패해도 나머지는 계속한다
                    errors[type(e).__name__] = errors.get(type(e).__name__, 0) + 1
            if point is None:
                out.append(replace(loc, geocode_status="failed"))
            else:
                out.append(replace(loc, lat=point.lat, lon=point.lon, geocode_status="ok", gu=loc.gu or point.gu))
        ctx.locations = out
        # 주소는 남기지 않고 오류 종류별 건수만 남긴다
        ctx.failures += [{"step": self.name, "error": k, "count": n} for k, n in sorted(errors.items())]
