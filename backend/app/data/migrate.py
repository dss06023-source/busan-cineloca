"""마이그레이션 러너: python -m app.data.migrate [DATABASE_URL]

migrations/NNN_<이름>.sql을 번호순으로 실행하고 적용한 번호를 schema_migrations에 남긴다.
머지한 파일은 고치지 않고 새 번호를 추가한다(build-plan 7장).
"""

import re
import sys
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "db" / "migrations"
_NAME = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")


def pending(applied: set[str], directory: Path = MIGRATIONS_DIR) -> list[Path]:
    files = sorted(p for p in directory.iterdir() if _NAME.match(p.name))
    return [p for p in files if _NAME.match(p.name).group(1) not in applied]


def migrate(dsn: str, directory: Path = MIGRATIONS_DIR) -> list[str]:
    done: list[str] = []
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version CHAR(3) PRIMARY KEY, name TEXT NOT NULL,"
            " applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        conn.commit()
        applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
        for path in pending(applied, directory):
            version = path.name[:3]
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations(version, name) VALUES (%s, %s)", (version, path.name))
            done.append(path.name)
    return done


def main() -> None:
    from app.config import get_settings

    dsn = sys.argv[1] if len(sys.argv) > 1 else get_settings().database_url
    applied = migrate(dsn)
    print("적용:", ", ".join(applied) if applied else "없음(최신)")


if __name__ == "__main__":
    main()
