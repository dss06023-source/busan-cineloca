"""배치 실행: python -m app.batch [--once]

sync_run의 요청(관리자 화면 API-021)을 1분마다 확인해 SyncJob을 돌린다(SDD CD-06 SyncScheduler).
--once는 요청 하나만 처리하고 끝낸다. 정기 실행(FR-616, Should)은 수동 요청으로 대신한다(build-plan 2장).
"""

import asyncio
import logging
import sys

from app.batch.job import IngestStep, SyncJob
from app.config import get_settings
from app.data.db import make_pool
from app.data.repositories.staging import StagingRepository
from app.data.repositories.sync import SyncRepository

POLL_S = 60


def build_steps() -> list[IngestStep]:
    # 수집·매칭·좌표·역·태그·AI 제안·출처·임베딩 단계는 WP-05 어댑터와 함께 붙인다.
    # 단계가 없으면 적재 건수가 0이라 건수 가드가 반영을 막는다
    return []


async def main(once: bool) -> None:
    pool = make_pool(get_settings().database_url)
    await pool.open()
    runs = SyncRepository(pool)
    job = SyncJob(build_steps(), StagingRepository(pool), runs)
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
