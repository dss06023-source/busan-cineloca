"""SQL은 data/repositories와 migrations에만 둔다(build-plan 4장). python -m app.tools.check_sql_location"""

import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
# 마이그레이션 러너와 시드 적재는 SQL 파일을 그대로 실행하는 도구라 예외로 둔다
ALLOWED = [APP / "data" / "repositories", APP / "data" / "migrate.py", APP / "data" / "seed.py"]
PATTERN = re.compile(r"\.execute(many)?\(")


def violations(root: Path = APP) -> list[str]:
    found = []
    for path in sorted(root.rglob("*.py")):
        if path == Path(__file__).resolve() or any(path.is_relative_to(a) for a in ALLOWED):
            continue
        for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if PATTERN.search(line):
                found.append(f"{path.relative_to(root.parent)}:{no}: {line.strip()}")
    return found


if __name__ == "__main__":
    bad = violations()
    for v in bad:
        print(v)
    sys.exit(1 if bad else 0)
