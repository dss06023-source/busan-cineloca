# 부산 씨네로케 (Busan CineLoca)

영화·드라마 속 부산 촬영지를 지도와 AI 탐색으로 안내하는 서비스입니다. 소프트웨어공학 팀 프로젝트.

- 구현 규칙: [AGENTS.md](AGENTS.md)
- 제작 설계안(작업 패키지 WP-01~12): [docs/build-plan.md](docs/build-plan.md)
- 설계서 SDD v0.1: [docs/sdd.md](docs/sdd.md), 다르게 만든 점: [docs/deviations.md](docs/deviations.md)

## 폴더

| 폴더 | 내용 |
|---|---|
| `backend/` | FastAPI API·배치(`app/api → services·pipeline → support → data`), 마이그레이션, 테스트 |
| `frontend/` | React + Vite + TypeScript SPA |
| `infra/` | docker compose, nginx, `.env.example`, DB init |
| `eval/` | AI 평가셋과 채점 스크립트(WP-12) |
| `docs/` | 설계 문서 |

## 실행 (docker compose)

```bash
cp infra/.env.example infra/.env        # 값 채우기(커밋 금지)
docker compose -f infra/docker-compose.yml up -d --build
curl http://localhost:8080/api/health   # {"db":"ok", ...}
```

휴대폰 시연은 `tailscale serve --bg 8080`으로 고정 HTTPS 주소를 엽니다(build-plan 3장).

## 개발

```bash
# 백엔드
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'
docker compose -f ../infra/docker-compose.yml up -d db       # 또는 로컬 PostgreSQL 16 + pgvector
python -m app.data.migrate postgresql://app:app@localhost:5432/cineloca
uvicorn app.main:app --reload
pytest -m "not integration"                                    # DB 없이
TEST_DATABASE_URL=postgresql://app:app@localhost:5432/postgres pytest   # 전체

# 프론트엔드
cd frontend && npm ci && npm run dev    # http://localhost:5173, /api는 8000으로 프록시
```

CI는 ruff, import-linter 계층 규칙, SQL 위치 규칙, pytest(실제 PostgreSQL), 프론트엔드 lint·tsc·vitest·build, gitleaks, compose 빌드를 PR마다 돌립니다.
