"""SyncJob(COMP-13, SDD CD-06): 단계를 차례로 돌려 stg에 적재하고, 건수 가드를 통과하면 반영한다.

실패하거나 가드를 어기면 반영하지 않고 sync_run에 이유를 남긴다(FR-612·613, ADR-012).
단계는 IngestStep을 따르는 객체이고, 실제 수집·매칭·좌표 단계는 WP-05 어댑터가 생기면 붙인다.
"""

import logging
from dataclasses import dataclass, field, replace
from typing import Protocol

from app.batch.guard import CountGuard
from app.data.models import StagedLocation, StagedShooting, StagedWork, SyncRun

log = logging.getLogger(__name__)


@dataclass
class SyncContext:
    """단계끼리 주고받는 적재 대상. 단계는 이 목록을 채우거나 고친다."""

    works: list[StagedWork] = field(default_factory=list)
    locations: list[StagedLocation] = field(default_factory=list)
    shootings: list[StagedShooting] = field(default_factory=list)
    # 레코드 단위 실패(단계 이름, 사유). URL·키는 넣지 않는다(SDD sync_run.failures)
    failures: list[dict] = field(default_factory=list)


class IngestStep(Protocol):
    name: str

    async def run(self, ctx: SyncContext) -> None: ...


class Staging(Protocol):
    async def load(self, works, locations, shootings) -> None: ...
    async def staged_counts(self) -> dict[str, int]: ...
    async def published_counts(self) -> dict[str, int]: ...
    async def publish(self) -> dict[str, int]: ...


class Runs(Protocol):
    async def save(self, run: SyncRun) -> None: ...


class SyncJob:
    def __init__(self, steps: list[IngestStep], staging: Staging, runs: Runs, guard: CountGuard | None = None):
        self.steps, self.staging, self.runs = steps, staging, runs
        self.guard = guard or CountGuard()

    async def run(self, run: SyncRun) -> SyncRun:
        ctx, step_counts, current = SyncContext(), {}, "load"
        try:
            for step in self.steps:
                current = step.name
                await step.run(ctx)
                step_counts[step.name] = {"work": len(ctx.works), "location": len(ctx.locations)}
            current = "load"
            await self.staging.load(ctx.works, ctx.locations, ctx.shootings)
            staged, prev = await self.staging.staged_counts(), await self.staging.published_counts()
            verdict = self.guard.check(staged, prev)
            counts = {**staged, "steps": step_counts, "guard": verdict.as_dict()}
            if not verdict.ok:
                result = replace(run, status="rejected", counts=counts, prev_counts=prev, failures=ctx.failures)
            else:
                current = "publish"
                counts |= {"published": await self.staging.publish()}
                result = replace(run, status="published", counts=counts, prev_counts=prev, failures=ctx.failures)
        except Exception as e:  # 어떤 단계가 터져도 서비스 데이터는 그대로 두고 기록만 남긴다
            # 예외 메시지에는 요청 URL·키가 섞일 수 있어 종류만 남긴다
            log.warning("동기화 %s 단계 실패: %s", current, type(e).__name__)
            failures = [*ctx.failures, {"step": current, "error": type(e).__name__}]
            result = replace(run, status="failed", counts={"steps": step_counts}, failures=failures)
        await self.runs.save(result)
        return result
