"""PolicyGuard(COMP-11, FR-703, BR-01): 어댑터 레코드를 저장소에 넘기기 전에 출처의 저장 정책을 강제한다.

STORE는 그대로, ID_ONLY는 식별자 필드만, NO_STORE는 아무것도 넘기지 않는다(None).
정책을 모르는 출처는 저장하지 않는 쪽으로 막는다.
"""

from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from typing import Any

from app.data.models import Source

# ID_ONLY 출처에서 남길 필드(SDD work.kmdb_id·kobis_movie_cd)
ID_FIELDS: dict[str, tuple[str, ...]] = {
    "DATA-04": ("kmdb_id",),
    "DATA-05": ("movie_cd",),
}


class PolicyViolation(Exception):
    pass


class PolicyGuard:
    def __init__(self, policies: Mapping[str, str]):
        self.policies = dict(policies)

    @classmethod
    def from_sources(cls, sources: Iterable[Source]) -> "PolicyGuard":
        return cls({s.id: s.policy for s in sources})

    def storable(self, source_id: str, record: Any) -> dict | None:
        policy = self.policies.get(source_id)
        row = asdict(record) if is_dataclass(record) else dict(record)
        if policy == "STORE":
            return row
        if policy == "ID_ONLY":
            fields = ID_FIELDS.get(source_id)
            if not fields:
                raise PolicyViolation(f"{source_id}: ID_ONLY인데 식별자 필드가 정해지지 않음")
            return {k: row[k] for k in fields if row.get(k) is not None} or None
        return None  # NO_STORE, 또는 정책을 모름

    def storable_all(self, source_id: str, records: Iterable[Any]) -> list[dict]:
        return [r for rec in records if (r := self.storable(source_id, rec)) is not None]
