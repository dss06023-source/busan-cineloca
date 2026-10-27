"""배치 실행: python -m app.batch [--once]

sync_run의 요청(관리자 화면 API-021)을 1분마다 확인해 SyncJob을 돌린다(SDD CD-06 SyncScheduler).
--once는 요청 하나만 처리하고 끝낸다. 정기 실행(FR-616, Should)은 수동 요청으로 대신한다(build-plan 2장).
"""

import asyncio
import logging
import sys

from psycopg_pool import AsyncConnectionPool

from app.batch.job import IngestStep, SyncJob
from app.batch.steps import MatchWorksStep
from app.config import Settings, get_settings
from app.data.adapters.kmdb_csv import KmdbCsvCatalog
from app.data.adapters.policy import PolicyGuard
from app.data.db import make_pool
from app.data.repositories.source import SourceRepository
from app.data.repositories.staging import StagingRepository
from app.data.repositories.sync import SyncRepository
from app.data.repositories.work import WorkRepository

POLL_S = 60


async def build_steps(settings: Settings, pool: AsyncConnectionPool) -> list[IngestStep]:
    # 수집·좌표·역·태그·AI 제안·출처·임베딩 단계는 WP-05 어댑터와 함께 붙인다.
    # 수집 단계가 없으면 적재 건수가 0이라 건수 가드가 반영을 막는다
    steps: list[IngestStep] = []
    if settings.kmdb_csv_path:  # KMDb 키 승인 전에는 CSV로 매칭한다(로드 약 8초)
        policy = PolicyGuard.from_sources(await SourceRepository(pool).all())
        catalog = KmdbCsvCatalog.load(settings.kmdb_csv_path)
        steps.append(MatchWorksStep(catalog, policy, WorkRepository(pool).reviewed_matches))
    return steps


async def main(once: bool) -> None:
    settings = get_settings()
    pool = make_pool(settings.database_url)
    await pool.open()
    runs = SyncRepository(pool)
    job = SyncJob(await build_steps(settings, pool), StagingRepository(pool), runs)
    try:
        while True:
            run = await runs.next_requested()
            if run:
                done = await job.run(run)
                logging.info("동기화 %s: %s", done.id, done.status)
            if once:
                return
            await asyncio.sleep(POLL_S)
    finally:
        await pool.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main("--once" in sys.argv))
