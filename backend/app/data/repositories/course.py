"""CourseRepository(COMP-12): 추천 코스(API-009·010·024). 사용자 저장 코스는 브라우저에만 있다."""

from psycopg_pool import AsyncConnectionPool

from app.data.models import Course, CourseStop
from app.data.repositories._rows import build

_COLS = "id, theme, theme_ref, title, start_label, start_lat, start_lon, total_min, total_m, status"


class CourseRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def approved(self, theme: str | None = None) -> list[Course]:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                f"SELECT {_COLS} FROM course WHERE status = 'approved'"
                " AND (%(theme)s::text IS NULL OR theme = %(theme)s) ORDER BY id",
                {"theme": theme},
            )
            return [build(Course, r) for r in await cur.fetchall()]

    async def all(self) -> list[Course]:
        """관리자용: 초안·승인 코스 전부(API-024)."""
        async with self.pool.connection() as conn:
            cur = await conn.execute(f"SELECT {_COLS} FROM course ORDER BY status = 'approved', id DESC")
            rows = await cur.fetchall()
        return [build(Course, {**r, "stops": await self.stops(r["id"])}) for r in rows]

    async def set_status(self, course_id: int, status: str, by: str) -> bool:
        """승인하면 승인자·시각을 남기고, 초안으로 돌리면 지운다(FR-614)."""
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "UPDATE course SET status = %(s)s::text,"
                " approved_by = CASE WHEN %(s)s::text = 'approved' THEN %(by)s END,"
                " approved_at = CASE WHEN %(s)s::text = 'approved' THEN now() END WHERE id = %(id)s",
                {"s": status, "by": by, "id": course_id},
            )
            return cur.rowcount == 1

    async def get(self, course_id: int) -> Course | None:
        async with self.pool.connection() as conn:
            cur = await conn.execute(f"SELECT {_COLS} FROM course WHERE id = %(id)s", {"id": course_id})
            row = await cur.fetchone()
        if row is None:
            return None
        stops = await self.stops(course_id)
        return build(Course, {**row, "stops": stops})

    async def stops(self, course_id: int) -> list[CourseStop]:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT ord, location_id, dwell_min, leg_mode, leg_min, leg_line FROM course_stop"
                " WHERE course_id = %(id)s ORDER BY ord",
                {"id": course_id},
            )
            return [build(CourseStop, r) for r in await cur.fetchall()]

    async def save(self, course: Course) -> int:
        """새 코스면 넣고, id가 있으면 덮어쓴다. 정류장은 지우고 다시 넣는다."""
        values = {k: getattr(course, k) for k in _COLS.split(", ") if k != "id"}
        async with self.pool.connection() as conn, conn.transaction():
            if course.id is None:
                cur = await conn.execute(
                    "INSERT INTO course(theme, theme_ref, title, start_label, start_lat, start_lon, total_min,"
                    " total_m, status) VALUES (%(theme)s, %(theme_ref)s, %(title)s, %(start_label)s,"
                    " %(start_lat)s, %(start_lon)s, %(total_min)s, %(total_m)s, %(status)s) RETURNING id",
                    values,
                )
                course_id = (await cur.fetchone())["id"]
            else:
                course_id = course.id
                await conn.execute(
                    "UPDATE course SET theme = %(theme)s, theme_ref = %(theme_ref)s, title = %(title)s,"
                    " start_label = %(start_label)s, start_lat = %(start_lat)s, start_lon = %(start_lon)s,"
                    " total_min = %(total_min)s, total_m = %(total_m)s, status = %(status)s::text,"
                    " approved_by = CASE WHEN %(status)s::text = 'approved' THEN approved_by END,"
                    " approved_at = CASE WHEN %(status)s::text = 'approved' THEN now() END WHERE id = %(id)s",
                    {**values, "id": course_id},
                )
                await conn.execute("DELETE FROM course_stop WHERE course_id = %(id)s", {"id": course_id})
            for stop in course.stops:
                await conn.execute(
                    "INSERT INTO course_stop(course_id, ord, location_id, dwell_min, leg_mode, leg_min, leg_line)"
                    " VALUES (%(c)s, %(ord)s, %(location_id)s, %(dwell_min)s, %(leg_mode)s, %(leg_min)s,"
                    " %(leg_line)s)",
                    {"c": course_id, **stop.__dict__},
                )
        return course_id
