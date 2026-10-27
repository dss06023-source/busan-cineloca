"""GroundingVerifier·EntityLexicon·PhraseFilter(COMP-09, AI-REQ-01·06·07).

LLM 문장은 근거 묶음에 있는 이름·숫자만 쓸 수 있다. 근거 밖 항목이 하나라도 있거나 결말·반전 표현이
있으면 그 문장을 지운다. 지운 뒤 어떻게 강등할지는 부른 쪽(F1·F3·F4)이 정한다.
"""

import re
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

# 연도, 분·시간, m·km. 숫자만 떼어 근거의 숫자와 맞춘다
_NUMBER_PATTERNS = [
    re.compile(r"((?:19|20)\d{2})\s*년?"),
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:분|시간)"),
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:km|m|킬로미터|미터)\b", re.IGNORECASE),
]
_ANY_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _norm(s: str) -> str:
    """공백·괄호·따옴표를 지우고 소문자로. 「가상 영화」와 '가상영화'를 같게 본다."""
    return re.sub(r"[\s「」『』\"'“”‘’()（）\[\]<>·.,]", "", s).lower()


def _num(s: str) -> str:
    return s.rstrip("0").rstrip(".") if "." in s else s


def _strings(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, bool) or value is None:
        return
    elif isinstance(value, int | float):
        yield str(value)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list | tuple | set):
        for v in value:
            yield from _strings(v)


class EntityLexicon:
    """지식베이스의 작품·인물·장소·구·군 이름. 문장에서 이 이름들을 찾는다."""

    def __init__(self, names: Iterable[str]):
        # 긴 이름부터 찾고, 찾은 자리는 지워서 '가상 영화 E2' 안의 '가상 영화 E'를 따로 세지 않는다
        self.names = sorted({n for n in names if n and len(_norm(n)) >= 2}, key=len, reverse=True)

    def find(self, text: str) -> list[str]:
        found: list[str] = []
        rest = text
        for name in self.names:
            if name in rest:
                found.append(name)
                rest = rest.replace(name, " ")
        return found


class PhraseFilter:
    """결말·반전 표현 목록(config/spoiler_phrases.yaml)에 걸리는 문장을 찾는다."""

    def __init__(self, phrases: Iterable[str]):
        self.phrases = [p for p in phrases if p]

    @classmethod
    def from_config(cls, path: Path = CONFIG_DIR / "spoiler_phrases.yaml") -> "PhraseFilter":
        return cls(_load_phrases(path))

    def hit(self, text: str) -> str | None:
        for p in self.phrases:
            if p in text:
                return p
        return None


@cache
def _load_phrases(path: Path) -> tuple[str, ...]:
    return tuple(yaml.safe_load(path.read_text(encoding="utf-8"))["phrases"])


@dataclass
class Verified:
    sentences: list[dict]
    dropped: list[dict] = field(default_factory=list)

    @property
    def texts(self) -> list[str]:
        return [s["text"] for s in self.sentences]


class GroundingVerifier:
    def __init__(self, lexicon: EntityLexicon, phrases: PhraseFilter | None = None):
        self.lexicon = lexicon
        self.phrases = phrases

    @staticmethod
    def gate(evidence: object) -> bool:
        """근거 묶음이 비면 False: LLM을 부르지 않는다(AI-REQ-01)."""
        return any(s.strip() for s in _strings(evidence))

    def verify(self, sentences: list[dict], evidence: object, spoiler_check: bool = True) -> Verified:
        values = list(_strings(evidence))
        blob = "|".join(_norm(v) for v in values)  # 값 경계를 남겨 두 값이 붙어 새 이름이 되지 않게
        numbers = {_num(n) for v in values for n in _ANY_NUMBER.findall(v)}
        kept, dropped = [], []
        for s in sentences:
            reason = self._reject_reason(s, blob, numbers, spoiler_check)
            if reason:
                dropped.append({**s, "reason": reason})
            else:
                kept.append(s)
        return Verified(kept, dropped)

    def _reject_reason(self, s: dict, blob: str, numbers: set[str], spoiler_check: bool) -> str | None:
        text = s.get("text", "")
        if spoiler_check and self.phrases and (p := self.phrases.hit(text)):
            return f"phrase:{p}"
        for name in [*self.lexicon.find(text), *s.get("entities", [])]:
            key = str(name)
            if _ANY_NUMBER.fullmatch(key.strip()):
                if _num(key.strip()) not in numbers:
                    return f"number:{key}"
            elif _norm(key) and _norm(key) not in blob:
                return f"entity:{key}"
        for pattern in _NUMBER_PATTERNS:
            for n in pattern.findall(text):
                if _num(n) not in numbers:
                    return f"number:{n}"
        return None


class LexiconCache:
    """EntityLexicon을 지식베이스 이름으로 만들어 ttl_s 동안 쓴다."""

    def __init__(self, load: Callable[[], Awaitable[list[str]]], ttl_s: float = 600, clock=time.monotonic):
        self.load = load
        self.ttl_s = ttl_s
        self.clock = clock
        self._at: float | None = None
        self._lexicon: EntityLexicon | None = None

    async def get(self) -> EntityLexicon:
        now = self.clock()
        if self._lexicon is None or now - self._at > self.ttl_s:
            self._lexicon, self._at = EntityLexicon(await self.load()), now
        return self._lexicon
