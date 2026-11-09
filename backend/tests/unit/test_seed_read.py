"""시드 파일 읽기: pg_dump 버전 차이로 생기는 줄을 걸러 낸다."""

from app.data.seed import read_sql


def test_read_sql_drops_meta_commands_and_pg17_settings(tmp_path):
    dump = tmp_path / "seed.sql"
    dump.write_text(
        "\\restrict abc\nSET statement_timeout = 0;\nSET transaction_timeout = 0;\n"
        "INSERT INTO t VALUES (1);\n\\unrestrict abc\n",
        encoding="utf-8",
    )
    assert read_sql(dump) == "SET statement_timeout = 0;\nINSERT INTO t VALUES (1);"
