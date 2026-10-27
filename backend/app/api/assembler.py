"""ResponseAssembler(COMP-02, ADR-014): 서비스가 돌려준 source_ids를 출처 카드로 바꿔 붙인다."""

from datetime import date

from pydantic import BaseModel

from app.support.sources import SourceRegistry, UnknownSource


class SourceCardOut(BaseModel):
    id: str
    org: str
    name: str
    base_date: date | None
    url: str


class Assembler:
    def __init__(self, registry: SourceRegistry):
        self.registry = registry

    async def cards(self, source_ids: list[str]) -> list[SourceCardOut]:
        """대장을 처음 쓰거나 모르는 ID가 오면 한 번 다시 읽는다(시작 때 DB가 늦게 뜬 경우, 시드 적재 뒤)."""
        try:
            cards = self.registry.cards(source_ids)
        except UnknownSource:
            await self.registry.reload()
            cards = self.registry.cards(source_ids)
        return [SourceCardOut(**c.__dict__) for c in cards]
