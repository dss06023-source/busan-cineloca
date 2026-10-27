"""시드 적재·내보내기(build-plan 7장 '시드 데이터').

  python -m app.data.seed load <파일.sql|파일.sql.gz> [DATABASE_URL]
  python -m app.data.seed export <파일.sql.gz> [DATABASE_URL]

적재는 마이그레이션을 먼저 적용한 빈 DB에 한다. 내보내기는 pg_dump가 필요하고, AI 캐시·호출 수·동기화
기록은 데이터를 빼고 내보낸다. 전체 시드는 GitHub Release에 올리고 저장소에는 넣지 않는다.
"""

import gzip
import subprocess
import sys
from pathlib import Path

import psycopg

from app.data.migrate import migrate

EXCLUDE_DATA = ("ai_cache", "usage_counter", "sync_run", "schema_migrations")


def read_sql(path: Path) -> str:
    text = gzip.decompress(path.read_bytes()).decode("utf-8") if path.suffix == ".gz" else path.read_text("utf-8")
    # pg_dump 16.10 이후의 \restrict 같은 psql 메타 명령은 서버 SQL이 아니므로 뺀다
    return "\n".join(line for line in text.splitlines() if not line.startswith("\\"))


def load(dsn: str, path: Path) -> None:
    migrate(dsn)
    with psycopg.connect(dsn, autocommit=True) as conn:
        if conn.execute("SELECT EXISTS (SELECT 1 FROM location)").fetchone()[0]:
            raise SystemExit("location에 이미 행이 있습니다. 빈 DB에만 적재합니다.")
        conn.execute(read_sql(path))


def export_command(dsn: str) -> list[str]:
    # 스키마는 마이그레이션이 만들므로 데이터만. 004_sources가 넣은 출처 행은 겹쳐도 건너뛴다.
    cmd = ["pg_dump", "--no-owner", "--data-only", "--column-inserts", "--on-conflict-do-nothing"]
    cmd += [f"--exclude-table-data={t}" for t in EXCLUDE_DATA]
    return [*cmd, dsn]


def export(dsn: str, path: Path) -> None:
    dump = subprocess.run(export_command(dsn), check=True, capture_output=True).stdout
    path.write_bytes(gzip.compress(dump))


def main(argv: list[str]) -> None:
    from app.config import get_settings

    if len(argv) < 2 or argv[0] not in ("load", "export"):
        raise SystemExit(__doc__)
    dsn = argv[2] if len(argv) > 2 else get_settings().database_url
    (load if argv[0] == "load" else export)(dsn, Path(argv[1]))
    print(f"{argv[0]}: {argv[1]}")


if __name__ == "__main__":
    main(sys.argv[1:])
