"""PromptRegistry: prompts/<작업>.v<번호>.md를 읽어 채운다.

파일은 '## system'과 '## user' 두 절로 나뉘고, user 절의 {inputs}에 입력 JSON, {user_input}에 사용자 문장이 들어간다.
사용자 문장은 <user_input> 태그 안에만 넣는다(AI-REQ-09).
"""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parents[3] / "prompts"


@dataclass(frozen=True)
class Prompt:
    task: str
    system: str
    user: str
    version: str


@cache
def _read(task: str, version: str, directory: Path) -> tuple[str, str]:
    text = (directory / f"{task}.{version}.md").read_text(encoding="utf-8")
    _, _, rest = text.partition("## system")
    system, _, user = rest.partition("## user")
    if not system.strip() or not user.strip():
        raise ValueError(f"{task}.{version}.md에 '## system'과 '## user' 절이 필요합니다")
    return system.strip(), user.strip()


def render(task: str, version: str, inputs: dict, directory: Path = PROMPT_DIR) -> Prompt:
    system, user = _read(task, version, directory)
    user_text = str(inputs.get("user_input", "")).replace("</user_input>", "")
    rest = {k: v for k, v in inputs.items() if k != "user_input"}
    body = user.replace("{inputs}", json.dumps(rest, ensure_ascii=False, indent=1))
    body = body.replace("{user_input}", user_text)
    return Prompt(task=task, system=system, user=body, version=version)
