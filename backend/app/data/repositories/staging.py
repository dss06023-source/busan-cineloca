"""StagingRepository(COMP-12): stg 적재와 public 반영(ADR-012, build-plan 7장 '동기화 반영 규칙').

반영은 한 트랜잭션이다. 촬영지·작품은 ext_key로 UPSERT해 id를 유지하고, 관리자가 고친 값은 덮어쓰지 않는다.
"""

from dataclasses import asdict

from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from app.data.models import StagedLocation, StagedShooting, StagedWork

_WORK_COLS = (
    "ext_key, title, title_norm, release_year, genres, kmdb_id, kobis_movie_cd, match_status, match_score, source_id"
)
_LOC_COLS = "ext_key, name, name_norm, address, gu, lat, lon, geocode_status, nearest_station_id, station_walk_min"


def _insert(table: str, cols: str) -> str:
    return f"INSERT INTO {table}({cols}) VALUES ({', '.join(f'%({c.strip()})s' for c in cols.split(','))})"


# 관리자가 검수로 연결한 작품(match_status='reviewed')은 매칭 결과를 그대로 둔다
_PUBLISH_WORK = f"""
INSERT INTO work({_WORK_COLS}) SELECT {_WORK_COLS} FROM stg.work
ON CONFLICT (ext_key) DO UPDATE SET
  retired = false, title = EXCLUDED.title, title_norm = EXCLUDED.title_norm,
  release_year = EXCLUDED.release_year, genres = EXCLUDED.genres,
  kobis_movie_cd = EXCLUDED.kobis_movie_cd, source_id = EXCLUDED.source_id,
  kmdb_id = CASE WHEN work.match_status = 'reviewed' THEN work.kmdb_id ELSE EXCLUDED.kmdb_id END,
  match_status = CASE WHEN work.match_status = 'reviewed' THEN 'reviewed' ELSE EXCLUDED.match_status END,
  match_score = CASE WHEN work.match_status = 'reviewed' THEN work.match_score ELSE EXCLUDED.match_score END
"""

# tags·caution·safety_note·cert_*는 원본에 없는 관리자 값이라 넣지 않는다.
# geocode_status가 manual인 행은 좌표와 그 좌표로 구한 최근접 역을 유지한다
_PUBLISH_LOCATION = f"""
INSERT INTO location({_LOC_COLS}) SELECT {_LOC_COLS} FROM stg.location
ON CONFLICT (ext_key) DO UPDATE SET
  retired = false, name = EXCLUDED.name, name_norm = EXCLUDED.name_norm,
  address = EXCLUDED.address, gu = EXCLUDED.gu,
  lat = CASE WHEN location.geocode_status = 'manual' THEN location.lat ELSE EXCLUDED.lat END,
  lon = CASE WHEN location.geocode_status = 'manual' THEN location.lon ELSE EXCLUDED.lon END,
  nearest_station_id = CASE WHEN location.geocode_status = 'manual' THEN location.nearest_station_id
                            ELSE EXCLUDED.nearest_station_id END,
  station_walk_min = CASE WHEN location.geocode_status = 'manual' THEN location.station_walk_min
                          ELSE EXCLUDED.station_walk_min END,
  geocode_status = CASE WHEN location.geocode_status = 'manual' THEN 'manual' ELSE EXCLUDED.geocode_status END
"""

_PUBLISH_SHOOTING = """
INSERT INTO shooting(work_id, location_id, source_id, raw, base_date)
SELECT w.id, l.id, s.source_id, s.raw, s.base_date
FROM stg.shooting s JOIN work w ON w.ext_key = s.work_key JOIN location l ON l.ext_key = s.location_key
"""

_COUNTS = (
    "SELECT (SELECT count(*) FROM {s}work{r}) AS work, (SELECT count(*) FROM {s}location{r}) AS location,"
    " (SELECT count(*) FROM {s}shooting) AS shooting"
)


class StagingRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def load(self, works: list[StagedWork], locations: list[StagedLocation],
                   shootings: list[StagedShooting]) -> None:  # fmt: skip
        """stg를 비우고 새로 적재한다."""
        async with self.pool.connection() as conn, conn.transaction(), conn.cursor() as cur:
            await cur.execute("TRUNCATE stg.shooting, stg.work, stg.location")
            await cur.executemany(_insert("stg.work", _WORK_COLS), [asdict(w) for w in works])
            await cur.executemany(_insert("stg.location", _LOC_COLS), [asdict(x) for x in locations])
            await cur.executemany(
                _insert("stg.shooting", "work_key, location_key, source_id, raw, base_date"),
                [{**asdict(s), "raw": Jsonb(s.raw)} for s in shootings],
            )

    async def staged_counts(self) -> dict[str, int]:
        return await self._counts(_COUNTS.format(s="stg.", r=""))

    async def published_counts(self) -> dict[str, int]:
        """지금 서비스 중인(retired가 아닌) 건수. 건수 가드의 '직전' 값이다."""
        return await self._counts(_COUNTS.format(s="", r=" WHERE NOT retired"))

    async def publish(self) -> dict[str, int]:
        """stg를 public에 한 트랜잭션으로 반영하고 반영 뒤 건수를 돌려준다."""
        async with self.pool.connection() as conn, conn.transaction(), conn.cursor() as cur:
            await cur.execute(_PUBLISH_WORK)
            await cur.execute("UPDATE work SET retired = true WHERE ext_key NOT IN (SELECT ext_key FROM stg.work)")
            await cur.execute(_PUBLISH_LOCATION)
            await cur.execute(
                "UPDATE location SET retired = true WHERE ext_key NOT IN (SELECT ext_key FROM stg.location)"
            )
            # 촬영 관계는 id를 맞춘 뒤 지우고 다시 넣는다
            await cur.execute("DELETE FROM shooting")
            await cur.execute(_PUBLISH_SHOOTING)
        return await self.published_counts()

    async def _counts(self, sql: str) -> dict[str, int]:
        async with self.pool.connection() as conn:
            cur = await conn.execute(sql)
            return dict(await cur.fetchone())
