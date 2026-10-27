#!/usr/bin/env bash
# E2E 실행: 빈 DB를 만들어 마이그레이션·미니 시드를 넣고 Playwright를 돌린다.
# 필요: PostgreSQL(pgvector), backend/.venv, frontend node_modules, Playwright 브라우저.
#   E2E_ADMIN_URL=postgresql://app:app@localhost/postgres e2e/run.sh [playwright 인자]
set -euo pipefail
cd "$(dirname "$0")/.."
ADMIN_URL=${E2E_ADMIN_URL:-postgresql://app:app@localhost/postgres}
DB=cl_e2e
export E2E_DATABASE_URL=${ADMIN_URL%/*}/$DB
export E2E_LOG_DIR=${E2E_LOG_DIR:-$(mktemp -d)}
psql "$ADMIN_URL" -qc "DROP DATABASE IF EXISTS $DB WITH (FORCE)" -c "CREATE DATABASE $DB"
(cd ../backend && .venv/bin/python -m app.data.migrate "$E2E_DATABASE_URL" \
  && .venv/bin/python -m app.data.seed load ../infra/seed/mini_seed.sql "$E2E_DATABASE_URL")
npx playwright test "$@"
