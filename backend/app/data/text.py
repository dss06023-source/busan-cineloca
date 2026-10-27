"""이름 정규화: 저장할 때와 질의할 때 같은 규칙을 쓴다(build-plan 7장 '사전 대조에서 잰 값')."""

import re
import unicodedata

_STRIP = re.compile(r"[\s\W_]+", re.UNICODE)


def normalize(text: str) -> str:
    """NFKC → 소문자 → 공백·기호 제거. '마 동석' → '마동석', '범죄도시 2' → '범죄도시2'"""
    return _STRIP.sub("", unicodedata.normalize("NFKC", text).lower())
