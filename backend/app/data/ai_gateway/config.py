"""config/ai.yaml 읽기."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"


@dataclass(frozen=True)
class ProviderConf:
    model: str
    min_timeout_s: float
    rpm: int
    daily_limit: int
    enabled: bool = True
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TaskConf:
    name: str
    chain: list[str]
    cap_s: float
    prompt: str
    schema: str


@dataclass(frozen=True)
class AIConfig:
    deadline_s: float
    reserve_s: float
    providers: dict[str, ProviderConf]
    tasks: dict[str, TaskConf]
    embedder: dict
    breaker_fails: int
    breaker_open_s: float
    cache_ttl_h: int
    usage_warn_ratio: float


def load_config(path: Path = CONFIG_DIR / "ai.yaml") -> AIConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    providers = {}
    for name, p in raw["providers"].items():
        base = {k: p[k] for k in ("model", "min_timeout_s", "rpm", "daily_limit")}
        extra = {k: v for k, v in p.items() if k not in (*base, "enabled")}
        providers[name] = ProviderConf(**base, enabled=p.get("enabled", True), extra=extra)
    tasks = {name: TaskConf(name=name, **t) for name, t in raw["tasks"].items()}
    return AIConfig(
        deadline_s=raw["deadline_s"],
        reserve_s=raw["reserve_s"],
        providers=providers,
        tasks=tasks,
        embedder=raw["embedder"],
        breaker_fails=raw["breaker"]["fails"],
        breaker_open_s=raw["breaker"]["open_s"],
        cache_ttl_h=raw["cache_ttl_h"],
        usage_warn_ratio=raw["usage_warn_ratio"],
    )
