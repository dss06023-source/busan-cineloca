"""SourceRegistry(COMP-15): 출처 ID → 출처 카드, 출처 대장·라이선스 목록(FR-704·705, NFR-008).

출처는 12건뿐이라 앱 시작 때 한 번 읽어 메모리에 두고, 동기화가 기준일을 바꾸면 reload()한다.
"""

from app.data.models import Source, SourceCard
from app.data.repositories.source import SourceRepository

# KOBIS 약관 6조 5항: 통합전산망 오픈 API 이용 표시(FR-705)
KOBIS_NOTICE = "이 서비스는 영화진흥위원회 영화관입장권 통합전산망의 오픈 API를 이용합니다."


class UnknownSource(KeyError):
    pass


class SourceRegistry:
    def __init__(self, repo: SourceRepository):
        self.repo = repo
        self._by_id: dict[str, Source] = {}

    async def reload(self) -> None:
        self._by_id = {s.id: s for s in await self.repo.all()}

    def cards(self, source_ids: list[str]) -> list[SourceCard]:
        """중복을 빼고 받은 순서대로 카드를 만든다. 대장에 없는 ID는 출처 누락이라 오류로 드러낸다."""
        cards = []
        for sid in dict.fromkeys(source_ids):
            s = self._by_id.get(sid)
            if s is None:
                raise UnknownSource(sid)
            cards.append(SourceCard(id=s.id, org=s.org, name=s.name, base_date=s.base_date, url=s.url))
        return cards

    def ledger(self) -> list[Source]:
        return list(self._by_id.values())

    def licenses(self) -> list[dict]:
        return [{"source_id": s.id, "license": s.license, "policy": s.policy} for s in self._by_id.values()]

    @staticmethod
    def kobis_notice() -> str:
        return KOBIS_NOTICE
