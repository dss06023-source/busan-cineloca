"""StationRepository(COMP-12): 도시철도 역과 역간 소요시간(DATA-08·09)."""

from psycopg_pool import AsyncConnectionPool

from app.data.models import Point, Station
from app.data.repositories._rows import build

_COLS = "id, name, line, lat, lon, gu"


class StationRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def all(self) -> list[Station]:
        async with self.pool.connection() as conn:
            cur = await conn.execute(f"SELECT {_COLS} FROM station ORDER BY line, id")
            return [build(Station, r) for r in await cur.fetchall()]

    async def get(self, station_id: str) -> Station | None:
        async with self.pool.connection() as conn:
            cur = await conn.execute(f"SELECT {_COLS} FROM station WHERE id = %(id)s", {"id": station_id})
            row = await cur.fetchone()
        return build(Station, row) if row else None

    async def nearest(self, p: Point) -> Station | None:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                f"SELECT {_COLS} FROM station"
                " ORDER BY earth_distance(ll_to_earth(%(lat)s, %(lon)s), ll_to_earth(lat, lon)), id LIMIT 1",
                {"lat": p.lat, "lon": p.lon},
            )
            row = await cur.fetchone()
        return build(Station, row) if row else None

    async def rail_minutes(self, a: str, b: str) -> float | None:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT minutes FROM station_time WHERE from_id = %(a)s AND to_id = %(b)s", {"a": a, "b": b}
            )
            row = await cur.fetchone()
        return row["minutes"] if row else None
