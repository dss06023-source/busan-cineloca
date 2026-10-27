"""config/adapters.yaml 읽기."""

from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"


@dataclass(frozen=True)
class AdapterConf:
    name: str
    source_id: str
    base_url: str
    timeout_s: float
    page_size: int
    daily_limit: int
    quota_ratio: float = 0.8
    retries: int = 3
    backoff_s: float = 1.0

    @property
    def quota(self) -> int:
        """하루에 실제로 쓸 호출 수(한도의 80%)."""
        return int(self.daily_limit * self.quota_ratio)


def load_adapters(path: Path = CONFIG_DIR / "adapters.yaml") -> dict[str, AdapterConf]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    common = {k: raw[k] for k in ("quota_ratio", "retries", "backoff_s")}
    return {name: AdapterConf(name=name, **common, **a) for name, a in raw["adapters"].items()}
