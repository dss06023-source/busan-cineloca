"""SchemaValidator: config/schemas/<이름>.json으로 LLM 출력을 검증한다(AI-REQ-04)."""

import json
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator

from app.data.ai_gateway.config import CONFIG_DIR
from app.data.ai_gateway.errors import SchemaError


@cache
def load_schema(name: str, directory: Path = CONFIG_DIR / "schemas") -> dict:
    return json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))


def validate(data: object, schema: dict) -> dict:
    if not isinstance(data, dict):
        raise SchemaError("JSON 객체가 아님")
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        raise SchemaError("; ".join(f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors[:3]))
    return data


def parse_json(text: str) -> object:
    """모델이 코드 블록으로 감싸 보내는 경우만 벗긴다. 그 밖의 잡음은 스키마 위반으로 본다."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rsplit("```", 1)[0]
    try:
        return json.loads(t)
    except json.JSONDecodeError as e:
        raise SchemaError(f"JSON 파싱 실패: {e.msg}") from None
