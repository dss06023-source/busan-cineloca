"""PrivacyGuard(COMP-10): 전화번호·이메일·주민등록번호·카드번호를 [개인정보]로 바꾸고 종류만 남긴다(FR-702).

로그 레코드는 모두 scrub()을 거친다(NFR-003·005). 좌표는 프롬프트에 넣지 않는다(BR-10): mask_inputs()가 좌표 키를 뺀다.
"""

import re
from typing import Any

MASK = "[개인정보]"

# 한글이 바로 붙어도 잡히도록 \b 대신 '앞뒤가 숫자가 아님'을 쓴다(파이썬에서 한글은 \w라 \b가 생기지 않음)
_PATTERNS = [
    ("rrn", re.compile(r"(?<!\d)\d{6}[- ]?[1-4]\d{6}(?!\d)")),
    ("card", re.compile(r"(?<!\d)\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}(?!\d)")),
    ("phone", re.compile(r"(?<!\d)(?:01[016789][- .]?\d{3,4}[- .]?\d{4}|0\d{1,2}[- .]\d{3,4}[- .]\d{4})(?!\d)")),
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")),
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


COORD_KEYS = frozenset({"lat", "lng", "lon", "latitude", "longitude", "coords"})


def mask_inputs(inputs: dict) -> tuple[dict, list[str]]:
    """LLM에 보낼 입력 전체를 마스킹하고 좌표 키를 뺀다. 돌려준 종류 목록은 응답의 masked 표시에 쓴다."""
    kinds: list[str] = []

    def walk(v: Any) -> Any:
        if isinstance(v, str):
            out, k = mask(v)
            kinds.extend(x for x in k if x not in kinds)
            return out
        if isinstance(v, dict):
            return {key: walk(val) for key, val in v.items() if key not in COORD_KEYS}
        if isinstance(v, list | tuple):
            return [walk(x) for x in v]
        return v

    return walk(inputs), kinds
