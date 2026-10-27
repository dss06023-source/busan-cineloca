"""CountGuardStep 판정(FR-612, BR-14).

새 적재의 작품 또는 촬영지 수가 직전보다 30% 이상 줄거나 최소 기준(작품 50편, 촬영지 150곳)에
못 미치면 반영하지 않는다.
"""

from dataclasses import dataclass, field

# 종류 → (이름, 조사)
KINDS = {"work": ("작품", "이"), "location": ("촬영지", "가")}


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"ok": self.ok, "reasons": self.reasons}


@dataclass(frozen=True)
class CountGuard:
    min_work: int = 50
    min_location: int = 150
    max_drop: float = 0.30

    def check(self, new: dict[str, int], prev: dict[str, int]) -> GuardResult:
        reasons = []
        for kind, (label, josa) in KINDS.items():
            n, before, floor = new.get(kind, 0), prev.get(kind, 0), getattr(self, f"min_{kind}")
            if n < floor:
                reasons.append(f"{label} {n}건이 최소 기준 {floor}건보다 적습니다")
            # 첫 동기화(직전 0건)는 최소 기준만 본다
            if before and (before - n) / before >= self.max_drop:
                reasons.append(f"{label}{josa} 직전 {before}건에서 {n}건으로 {self.max_drop:.0%} 이상 줄었습니다")
        return GuardResult(not reasons, reasons)
