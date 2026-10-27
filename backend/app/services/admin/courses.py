"""추천 코스 후보 생성·승인(API-024, FR-614, SDD COMP-14 draft_course·approve_course).

후보는 테마(작품·인물·구)에 맞는 촬영지를 작품 수 순으로 고르고 RoutePlanner로 순서를 정한다.
승인된 코스만 사용자에게 보인다(API-009·010).
"""

from dataclasses import dataclass, replace
from typing import Literal

from app.data.models import Course, CourseStop, Point
from app.data.repositories.course import CourseRepository
from app.data.repositories.location import LocationRepository
from app.data.repositories.station import StationRepository
from app.data.repositories.work import WorkRepository
from app.pipeline.course.route import Place, Route, RoutePlanner, TravelModel
from app.pipeline.course.scoring import course_config
from app.pipeline.travel import haversine_m, station_label, walk_minutes
from app.services.admin.service import InvalidInput, NotFound

DRAFT_STOPS = 5  # 후보 코스 장소 수. 관리자가 고쳐서 3~8곳(course.yaml)
Theme = Literal["work", "actor", "area"]


@dataclass(frozen=True)
class AdminCourse:
    course: Course
    names: dict[int, str]  # location_id → 이름


class CourseAdmin:
    def __init__(self, courses: CourseRepository, locations: LocationRepository, stations: StationRepository,
                 works: WorkRepository):  # fmt: skip
        self.courses, self.locations, self.stations, self.works = courses, locations, stations, works
        self.conf = course_config()

    async def all(self) -> list[AdminCourse]:
        return [await self._with_names(c) for c in await self.courses.all()]

    async def draft_course(self, theme: Theme, ref: str, title: str | None = None) -> AdminCourse:
        """테마에 맞는 촬영지로 초안을 만든다. 사유지(caution=private)는 넣지 않는다(BR-06)."""
        default_title = await self._default_title(theme, ref)
        cands = [c for c in await self.locations.course_candidates() if c.caution != "private"]
        if theme == "work":
            cands = [c for c in cands if int(ref) in c.work_ids]
        elif theme == "actor":
            cands = [c for c in cands if int(ref) in c.person_ids]
        else:
            cands = [c for c in cands if c.gu == ref]
        cands.sort(key=lambda c: (-c.work_count, c.id))
        chosen = cands[:DRAFT_STOPS]
        if len(chosen) < self.conf["min_stops"]:
            raise InvalidInput(f"좌표가 있는 촬영지가 {len(chosen)}곳뿐이라 코스를 만들 수 없습니다")
        start = await self._station_start(chosen[0].nearest_station_id) or Place(
            None, chosen[0].name, chosen[0].lat, chosen[0].lon, chosen[0].nearest_station_id, chosen[0].station_walk_min
        )
        stops = [Place(c.id, c.name, c.lat, c.lon, c.nearest_station_id, c.station_walk_min) for c in chosen]
        route = (await self._planner()).plan(start, stops)
        course = _course_of(route, theme, ref, title or default_title, "draft")
        course_id = await self.courses.save(course)
        return await self._with_names(replace(course, id=course_id))

    async def update_course(self, course_id: int, by: str, stops: list[int] | None = None, title: str | None = None,
                            status: Literal["draft", "approved"] | None = None) -> AdminCourse:  # fmt: skip
        """장소를 바꾸면 그 순서로 다시 계산하고 초안으로 돌린다(다시 승인해야 공개)."""
        c = await self.courses.get(course_id)
        if c is None:
            raise NotFound(course_id)
        if stops is not None or title is not None:
            if stops is not None:
                c = await self._replan(c, stops)
            if title is not None:
                if not title.strip():
                    raise InvalidInput("title")
                c = replace(c, title=title.strip())
            c = replace(c, status="draft" if stops is not None else c.status)
            await self.courses.save(c)
        if status is not None:
            await self.courses.set_status(course_id, status, by)
        return await self._with_names(await self.courses.get(course_id))

    async def _replan(self, c: Course, ids: list[int]) -> Course:
        lo, hi = self.conf["min_stops"], self.conf["max_stops"]
        if len(set(ids)) != len(ids) or not lo <= len(ids) <= hi:
            raise InvalidInput(f"장소는 서로 다른 {lo}~{hi}곳")
        locs = await self.locations.many(ids)
        if len(locs) != len(ids) or any(x.lat is None for x in locs):
            raise InvalidInput("좌표가 있는 촬영지만 넣을 수 있습니다")
        st = await self.stations.nearest(Point(c.start_lat, c.start_lon))
        walk = walk_minutes(haversine_m(c.start_lat, c.start_lon, st.lat, st.lon)) if st else None
        start = Place(None, c.start_label, c.start_lat, c.start_lon, st.id if st else None, walk)
        places = [Place(x.id, x.name, x.lat, x.lon, x.nearest_station_id, x.station_walk_min) for x in locs]
        route = (await self._planner()).plan(start, places, fixed_order=True)
        return replace(_course_of(route, c.theme, c.theme_ref, c.title, c.status), id=c.id)

    async def _default_title(self, theme: Theme, ref: str) -> str:
        if theme == "area":
            return f"{ref} 촬영지 산책"
        if not ref.isdigit():
            raise InvalidInput("ref는 작품·인물 id")
        if theme == "work":
            w = await self.works.get(int(ref))
            if w is None:
                raise NotFound(ref)
            return f"「{w.work.title}」 따라 걷기"
        name = await self.works.person_name(int(ref))
        if name is None:
            raise NotFound(ref)
        return f"{name} 출연작 촬영지"

    async def _station_start(self, station_id: str | None) -> Place | None:
        s = await self.stations.get(station_id) if station_id else None
        return Place(None, station_label(s.name), s.lat, s.lon, s.id, 0) if s else None

    async def _planner(self) -> RoutePlanner:
        lines = {s.id: s.line for s in await self.stations.all()}
        return RoutePlanner(TravelModel(await self.stations.time_table(), lines), self.conf["dwell_min"])

    async def _with_names(self, c: Course) -> AdminCourse:
        locs = await self.locations.many([s.location_id for s in c.stops])
        return AdminCourse(c, {x.id: x.name for x in locs})


def _course_of(route: Route, theme: str, ref: str | None, title: str, status: str) -> Course:
    stops = [
        CourseStop(i + 1, p.id, route.dwell_min, leg.mode, leg.minutes, leg.line)
        for i, (p, leg) in enumerate(zip(route.stops, route.legs, strict=True))
    ]
    s = route.start
    return Course(theme, title, s.name, s.lat, s.lon, route.total_min, route.total_m, stops, ref, status)
