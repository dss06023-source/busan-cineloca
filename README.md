# 씨네로케 (CineLoca)

영화·드라마 속 부산 촬영지를 지도에서 찾고, 코스를 짜고, 방문을 인증하는 웹 서비스입니다.
소프트웨어공학 15팀 「하자제발」 프로젝트이고, 팀 공식 저장소는 [JaeWon0720/cineloca](https://github.com/JaeWon0720/cineloca)입니다.
이 저장소는 같은 설계 문서(SRS·SDD)로 먼저 만들어 본 구현입니다.

## 한눈에 보기

- **무엇을 하나**: 작품을 고르면 부산 촬영지를 지도에 보여 주고, "마동석 영화 촬영지 중 역에서 걸어서 10분"처럼 말로 물어도 찾아 줍니다.
- **어디까지 됐나 (11/9)**: 화면 12개와 API 25개 중 24개가 동작합니다. 실제 공공데이터로 작품 436편, 촬영지 1,378곳을 모았고, 촬영지 좌표는 주소 좌표 키를 받아 채우는 중입니다.
- **AI는 어디에 쓰나**: 말로 한 질문을 검색 조건으로 바꾸고, 결과·작품·코스를 설명하는 데만 씁니다. AI가 멈춰도 지도·검색·인증은 그대로 됩니다.

## 기능

| 기능 | 하는 일 | AI |
|---|---|---|
| F1 작품 | 작품 목록·상세, AI 작품 소개 | 소개 문장 |
| F2 지도 | 내 위치·역·구 기준 반경 검색, 촬영지 상세, 길찾기 | 없음 |
| F3 코스 | 추천 코스, 직접 고른 코스의 순서·시간 계산, AI 맞춤 코스 | 취향 정리, 코스 소개 |
| F4 AI 탐색 | 말로 묻고 조건 칩으로 다듬기 | 조건 추출, 결과 요약 |
| F5 방문 인증 | GPS로 방문 인증, 스탬프북, 완주 배지 | 없음 |
| C1 데이터 | 공공데이터 수집 → 주소 좌표 → 작품 매칭, 관리자 검수 화면 | 태그·매칭 제안(사람이 확인) |
| C2 출처 | 모든 결과에 출처 표시, 이용조건 안내 | 없음 |

## 폴더 안내

| 폴더 | 들어 있는 것 | 주로 보는 사람 |
|---|---|---|
| `frontend/` | React 화면, 카카오 지도 | R3 박동준 |
| `backend/` | API 서버, 데이터 수집 배치, 테스트 | R1 김예준, R2 정재원, R4 이승근 |
| `db/` | DB 테이블 정의(migrations), 개발용 가짜 데이터(seed) | R4 이승근 |
| `config/` | AI 모델·제한 시간, 외부 API, 코스 점수 설정 | R2 정재원 |
| `eval/` | AI 평가 문항 | R2 정재원 |
| `poc/` | 착수 확인 결과: 데이터 건수·좌표, AI 호출 | 모두 |
| `docs/` | 설계 문서 ([docs 안내](docs/README.md)) | 모두 |

루트의 `docker-compose.yml`은 전체 실행 구성이고, `.env.example`은 필요한 환경 변수 이름 목록입니다.
`AGENTS.md`·`CLAUDE.md`는 AI 코딩 도구가 읽는 작업 규칙이라 루트에 있어야 합니다.

### 역할별로 먼저 볼 곳

| 역할 | 담당 | 먼저 볼 곳 |
|---|---|---|
| R1 김예준 | 백엔드 구조, 경로 최적화, 방문 인증, 통합·배포 | `backend/app/api`, `backend/app/pipeline/course`, `backend/app/pipeline/certify.py`, `docker-compose.yml`, `.github/workflows` |
| R2 정재원 | AI 파이프라인, LLM 연결, 개인정보, AI 평가 | `backend/app/data/ai_gateway`, `backend/app/pipeline/query`, `backend/app/support`, `backend/prompts`, `config/ai.yaml` |
| R3 박동준 | 프론트엔드, 지도, UI/UX | `frontend/src/pages`, `frontend/src/components`, `docs/DESIGN.md` |
| R4 이승근 | 데이터 수집, 지식베이스, 검색 SQL, 테스트 | `backend/app/data/adapters`, `backend/app/data/repositories`, `backend/app/batch`, `db/` |

### 백엔드 안의 순서

```
api (요청 받기) → services·pipeline (기능 처리) → support (공통 도구) → data (DB·외부 API·AI 호출)
```

위에서 아래로만 부릅니다. SQL은 `data/repositories`와 `db/migrations`에만, 외부 호출은 `data/adapters`와 `data/ai_gateway`에만 둡니다. CI가 이 규칙을 검사합니다.

## 실행해 보기

**1. 백엔드 없이 화면만** (가장 쉬움, Node.js만 필요)

```bash
cd frontend && npm ci
VITE_USE_MOCKS=1 npm run dev        # http://localhost:5173
```

**2. 전체** (Docker 필요)

```bash
cp .env.example .env                # 키 값 채우기, 이 파일은 커밋 금지
docker compose up -d --build        # http://localhost:8080
docker compose exec api python -m app.data.seed load /srv/seed/mini_seed.sql   # 가짜 데이터 넣기(빈 DB에 한 번)
```

키가 없어도 가짜 데이터로 화면을 볼 수 있습니다. 다만 AI 기능은 `GEMINI_API_KEY`가 없으면 AI 없이 동작하는 안내 화면으로 바뀌고, 지도는 `VITE_KAKAO_JS_KEY`가 없으면 목록으로만 보입니다.

## 개발할 때

```bash
# 백엔드
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'
docker compose up -d db
python -m app.data.migrate postgresql://app:app@localhost:5432/cineloca
uvicorn app.main:app --reload
pytest -m "not integration"                                             # DB 없이
TEST_DATABASE_URL=postgresql://app:app@localhost:5432/postgres pytest   # DB 포함 전체

# 프론트엔드
cd frontend && npm ci && npm run dev    # /api는 localhost:8000으로 연결
```

- 실제 데이터 수집: `python -m app.batch --once` (수집 → 주소 좌표 → 작품 매칭)
- API를 바꾸면 `python -m app.tools.export_openapi ../frontend/src/api/openapi.json` 뒤 `npm run gen:api`로 프론트 타입을 다시 만듭니다.
- 시연 장면 5개 자동 확인(E2E): `cd frontend && E2E_ADMIN_URL=postgresql://app:app@localhost:5432/postgres e2e/run.sh`. 실제 AI 대신 가짜 응답(`AI_PROVIDERS=fake`)을 씁니다.

## 협업 규칙

- **브랜치**: main에 직접 push하지 않습니다. `feature/이슈번호-작업명`, `fix/…`, `docs/…`
- **커밋**: `feat: 촬영지 근접 검색 API 추가 (#21)`처럼 종류와 이슈 번호를 씁니다.
- **PR**: 템플릿(요구사항 ID, 테스트 결과, AI 활용 여부)을 채우고, 리뷰 1명 승인과 CI 통과 뒤 Squash and merge
- **CI**: PR마다 코드 검사, 계층 규칙, 테스트(실제 PostgreSQL), 프론트 빌드, 비밀키 검사, Docker 빌드를 돌립니다.
- **비밀키**: `.env`는 커밋하지 않고, 채팅에도 올리지 않습니다.

## 데이터 출처·이용조건

모든 결과에 출처 카드를 붙이고, 출처 화면에서 이용조건과 저장 정책을 안내합니다.
카카오 지도 응답, KOBIS 응답 본문, 영화 이미지 파일은 서버에 저장하지 않습니다.
