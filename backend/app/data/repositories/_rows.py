"""dict 행 → 값 객체 변환 도우미."""

from dataclasses import fields


def build(cls, row: dict):
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in row.items() if k in names})
