"""OpenAPI 문서를 파일로 쓴다: python -m app.tools.export_openapi ../frontend/src/api/openapi.json

CI는 다시 만든 결과가 커밋된 파일과 같은지 본다. 다르면 API 계약이 바뀐 것이므로 프론트 타입도 다시 만든다.
"""

import json
import sys
from pathlib import Path

from app.main import create_app


def main(path: str) -> None:
    spec = create_app().openapi()
    Path(path).write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
