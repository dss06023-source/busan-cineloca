"""PrivacyGuard(COMP-10) 최소판. WP-06이 마스킹 종류 기록과 가짜 개인정보 50건 테스트를 더한다.

로그 레코드는 모두 scrub()을 거친다(NFR-003·005).
"""

import re
from typing import Any

MASK = "[개인정보]"

_PATTERNS = [
    ("rrn", re.compile(r"\b\d{6}-?[1-4]\d{6}\b")),
    ("card", re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b")),
    ("phone", re.compile(r"\b01[016789][- ]?\d{3,4}[- ]?\d{4}\b|\b0\d{1,2}-\d{3,4}-\d{4}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
]


def mask(text: str) -> tuple[str, list[str]]:
    """개인정보를 [개인정보]로 바꾸고, 찾은 종류만 돌려준다."""
    kinds: list[str] = []
    for kind, pattern in _PATTERNS:
        text, n = pattern.subn(MASK, text)
        if n:
            kinds.append(kind)
    return text, kinds


def scrub(record: Any) -> Any:
    """로그 레코드 안의 모든 문자열을 마스킹한다."""
    if isinstance(record, str):
        return mask(record)[0]
    if isinstance(record, dict):
        return {k: scrub(v) for k, v in record.items()}
    if isinstance(record, list | tuple):
        return [scrub(v) for v in record]
    return record
