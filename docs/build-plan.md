# 부산 씨네로케 제작 설계안

2026-10-27 ·

구현 워커(사람이든 AI 코딩 에이전트든)가 이 문서와 SDD만 보고 같은 구조로 만들 수 있게 쓴 작업 지시서입니다. 제출용이 아니라서 강의·평가 설명은 빼고, 계획서·SRS·SDD의 ID(FR·API·COMP 등)는 원문을 찾아볼 수 있게 괄호로 남겼습니다. 워커는 10장의 작업 패키지 하나를 맡고, 12장의 공통 규칙을 지킵니다.

## 1. 한눈에 보기

11/26 MVP(G1)까지 Must 기능 7개(F1~F5, C1·C2)를 줄이지 않고 만듭니다. AI 없이 도는 뼈대를 먼저 세우고, AI 기능 3개(F1·F3·F4)는 공용 AI 게이트웨이 하나 위에 차례로 올립니다. 비용은 0원(K2)이고, 시연은 발표자 노트북 한 대로 합니다.

| 결정 | 제작 방식 | 기존 문서에서 바뀌는 점 |
|---|---|---|
| AI 공급자 | Gemini API 무료 티어(결제 미연결)가 기본입니다. 로컬 qwen3:8b는 GPU PC가 있을 때만 설정으로 켭니다 | 대체 체인 'Gemini → Ollama → 강등'이 'Gemini → 강등'이 되고 로컬은 선택 사항 |
| AI 시간 예산 | 요청마다 마감 7.5초를 두고, LLM 호출은 남은 시간 안에서만 기다립니다 | SDD 부록 B와 SRS FR-411·IF-09의 '조건 추출 10초'를 없앰(p95 8초 목표와 충돌) |
| 임베딩 | bge-m3를 Ollama CPU 모드로 상시 띄웁니다. 지식베이스 벡터는 시드 DB에 미리 넣습니다 | '팀 서버 GPU에서만 계산'이 '아무 PC에서나 계산' |
| 시연 환경 | 노트북에서 docker compose로 web·api·db·embed를 띄우고, 휴대폰은 Tailscale serve의 고정 HTTPS 주소로 접속합니다 | Cloudflare 터널과 '팀 서버' 삭제 |
| 제작 순서 | 첫 주에 손으로 만든 미니 시드(촬영지 20곳)로 '지도에 촬영지가 뜨는' 끝단 연결부터 만듭니다 | 임계 경로인 C1 배치(8일)를 기다리지 않고 화면·API를 함께 진행 |
| AI 게이트웨이 시점 | 스프린트 1에 C1 태깅 제안과 함께 만들고, 스프린트 2에는 작업별 프롬프트만 더합니다 | 가용 노력보다 약 6% 많던 스프린트 2 부하를 덜어 냄 |
| 용어 | 문서와 화면은 '촬영지', 코드는 location으로 통일합니다 | 계획서의 '작품지'를 정리 |

근거 문서는 계획서 v0.2, SRS v0.1(10/23), SDD v0.1(10/24)이고, 10/26 논의에서 정한 방향(Gemini 무료·로컬 선택, Tailscale 고정 주소, 용어 통일)을 반영했습니다. 팀이 아직 정하지 않은 값은 각 장에 '확인 필요'로 적었습니다.

## 2. 제작 범위

MVP는 SRS의 Must 요구사항(기능 77·비기능 17·AI 15)을 모두 담습니다. 그중 최종 발표 시연 경로(계획서 20.3)에 나오는 다섯 장면을 가장 먼저, 가장 매끄럽게 만듭니다.

1. 지도 홈에서 해운대 주변 촬영지 보기: F2, API-005·006, AI 없음
2. 작품 상세와 AI 소개: F1, API-002·003·004, LLM 1회
3. AI 탐색 "마동석 나온 영화 촬영지 중 지하철역에서 걸어서 10분 안": F4, API-013, LLM 2회
4. AI 맞춤 코스(서면 출발 반나절): F3, API-012, LLM 2회
5. 방문 인증과 스탬프북: F5, API-016·018, AI 없음

| 기능 | 만드는 것 | 화면 · API | 스프린트 | 일정이 밀리면(계획서 14.3 순서) |
|---|---|---|---|---|
| C1 지식베이스 | 촬영지 API 2종 수집·병합, KMDb 매칭·KOBIS ID, 주소 좌표, 최근접 역, 규칙 태그, AI 태그 제안·검수, 건수 가드, 임베딩(FR-601~615·617) | UI-10·11 · API-020~023 | S1 | 정기 동기화(FR-616, Should)는 수동 실행으로 대신 |
| C2 개인정보·출처 | 마스킹, 저장 정책 가드, 출처 카드, 데이터 출처 화면, 'AI 생성' 표시(FR-701~707) | UI-09 · API-019 | S1 | 줄이지 않음(과제 필수 조건) |
| F2 지도 탐색 | 근접 검색, 묶음 마커, 필터, 요약 카드, 촬영지 상세, 길찾기 링크(FR-201~210) | UI-01·02 · API-005~007 | S1 | 필터를 구·장르로 축소(⑤) |
| F1 작품 | 목록·상세·관람등급(S1), 스포일러 단계별 AI 소개(S2)(FR-101~111) | UI-03·04 · API-001~004 | S1·S2 | 스포일러 '일부' 단계 제거(④) |
| F4 AI 탐색 | 9단계 파이프라인, 필터 패널, 후속 질의, 해석 조건 칩(FR-401~412) | UI-05 · API-013~015 | S2 | 줄이지 않음(AI 핵심) |
| F3 코스 | 추천·나만의·AI 맞춤 코스, 최근접 이웃 + 2-opt, 시간 예산, 코스 저장(FR-301~313, 305 제외) | UI-06·07 · API-009~012, 024 | S2 | 도시철도 역간 시간 → 직선거리 보정 하나로(③) |
| F5 방문 인증 | 지오펜스, 서명 토큰, 스탬프북, 완주 배지(FR-501~509) | UI-02·08 · API-016~018 | S2 | 완주 배지 → 스탬프만(②) |

Should(FR-305·616·801~803)와 Could(FR-901~903)는 만들지 않고 확장 지점만 남깁니다. 착수 여부는 계획대로 11/23 스프린트 2 리뷰에서 정합니다(①).

## 3. 실행 환경과 배치

개발·시연은 같은 docker compose 구성 하나를 쓰고, 발표자 노트북 한 대에서 서비스 전체가 돕니다. GPU가 필요한 구성 요소는 없고, 휴대폰은 Tailscale serve가 주는 고정 HTTPS 주소로 접속합니다.

*(그림: 실행 배치 · 노트북 컨테이너 5개와 바깥 연결 3갈래 — 원본 Claude Doc 참고)*

휴대폰 요청은 Tailscale serve가 받아 web(8080)으로 넘기고, 바깥으로 나가는 호출은 api의 실시간 호출, batch의 수집, 브라우저의 카카오 SDK 세 갈래뿐입니다. embed는 batch도 씁니다(EmbedStep).

| 서비스 | 이미지·실행 | 역할 | 메모 |
|---|---|---|---|
| web | nginx + React 빌드 결과 | SPA 제공, /api 요청을 api로 전달 | 포트 8080 하나만 열어 같은 출처가 되므로 CORS 설정이 필요 없음 |
| api | python:3.12-slim, uvicorn 워커 1개 | API-001~025, 업무 서비스, AI 게이트웨이 | 워커 1개는 ADR-013(대화 맥락을 메모리에 둠) |
| db | pgvector/pgvector:pg16 | 지식베이스, AI 캐시, 호출 수 | pg_trgm·cube·earthdistance는 기본 포함 확장, 시드는 init 스크립트로 적재 |
| embed | ollama/ollama + bge-m3 | 질의·취향 문장 임베딩(CPU) | 모델 1.2GB, 첫 실행 때 한 번 내려받음 |
| batch | api와 같은 이미지, profiles: batch | 동기화 11단계(COMP-13), sync_run 요청 확인 | 평소에는 꺼 두고 관리자 동기화 시연 때만 켬 |

**휴대폰 시연 준비(처음 한 번)**

1. 노트북과 휴대폰에 Tailscale을 설치하고 같은 계정으로 로그인합니다(무료 개인 요금제).
2. 관리 콘솔에서 MagicDNS와 HTTPS 인증서를 켭니다.
3. `docker compose up -d` 뒤 `tailscale serve --bg 8080`을 실행하면 `https://<노트북 이름>.<tailnet 이름>.ts.net` 주소가 생깁니다. 이 주소는 바뀌지 않습니다.
4. 카카오 개발자 콘솔의 Web 플랫폼 사이트 도메인에 `http://localhost:8080`, `http://localhost:5173`(개발 서버), ts.net 주소 세 개를 등록합니다.
5. 시연이 끝나면 `tailscale serve reset`으로 끕니다. 청중 휴대폰까지 열 때만 `tailscale funnel`을 쓰고, 이때는 주소가 인터넷에 공개됩니다.

serve는 같은 tailnet의 기기만 들어올 수 있고 HTTPS를 Tailscale이 처리하므로, 휴대폰 브라우저의 위치 권한(IF-11)이 그대로 동작합니다([Tailscale Serve 문서](https://tailscale.com/docs/features/tailscale-serve), [CLI 참고](https://tailscale.com/docs/reference/tailscale-cli/serve.md)).

**키와 환경변수(.env.example에 이름만 올림)**

| 변수 | 쓰는 곳 | 값의 예 |
|---|---|---|
| GEMINI_API_KEY, GEMINI_MODEL | api | 시연용 Google Cloud 프로젝트의 키(결제 미연결), 모델명은 AI Studio에서 확인 |
| AI_PROVIDERS | api, batch | `gemini`(기본) 또는 `gemini,ollama`(GPU PC가 있을 때), 테스트는 `fake` |
| OLLAMA_URL, OLLAMA_LLM_URL | api, batch | `http://embed:11434`, 로컬 LLM은 선택(비워 두면 꺼짐) |
| KMDB_KEY, KOBIS_KEY, DATA_GO_KR_KEY, JUSO_KEY, TOUR_API_KEY | batch(KOBIS는 api, KMDb는 ID_ONLY일 때 api도) | 각 기관에서 발급 |
| VITE_KAKAO_JS_KEY | web 빌드 인자 | 브라우저에 노출되는 키라 등록 도메인으로 제한 |
| ADMIN_PASSWORD_HASH, TOKEN_KEYS | api | argon2 해시, `kid:비밀키` 목록(키 교체용) |
| DATABASE_URL, NOTICE_VERSION | api, batch | `postgresql://app:…@db:5432/cineloca`, `2026-11-01` |

Gemini 한도는 키가 아니라 프로젝트 단위라, 개발용과 시연용 키는 다른 프로젝트에서 만듭니다. 남는 비용은 없습니다. 도메인을 사지 않고, Tailscale·카카오·공공데이터·KMDb·KOBIS는 모두 무료입니다.

## 4. 저장소와 코드 구조

저장소는 하나이고, 백엔드 패키지는 SDD 2.1의 네 계층을 폴더 그대로 나눕니다. 폴더가 계층과 같으면 의존 규칙을 import-linter로 기계적으로 검사할 수 있습니다.

```text

```

계획서 17.2와 다른 점은 두 가지입니다. batch를 최상위 폴더에서 backend/app/batch로 옮겨 어댑터·저장소·AI 게이트웨이 코드를 그대로 같이 쓰고, adapters는 data/ 아래로 넣었습니다.

| 폴더 | 컴포넌트 | 작업 패키지(10장) | 첫 작업 |
|---|---|---|---|
| frontend/ | COMP-01 | WP-04(골격), 기능별 화면은 WP-08~11 | 하단 탭 5개 레이아웃, MapView |
| app/api/ | COMP-02 | WP-01(공통 미들웨어), 라우터는 기능별 WP | 오류 형식(ERR-xxx), X-Session-Id·X-Notice-Version 미들웨어 |
| services/map | COMP-04 | WP-03 | API-005 근접 검색 |
| services/archive | COMP-03 | WP-08 | API-001·002 작품 목록·상세 |
| services/query, pipeline/query | COMP-06 | WP-09 | QueryPipeline 골격과 가짜 LLM |
| services/course, pipeline/course | COMP-05 | WP-10 | RoutePlanner와 단위 테스트 |
| services/stamp | COMP-07 | WP-11 | Geofence·TokenSigner |
| support/, data/ai_gateway | COMP-08·09·10 | WP-06 | PrivacyGuard, GeminiProvider |
| data/adapters | COMP-11 | WP-05 | BaseApiClient, FilmLocationClient |
| data/repositories, migrations | COMP-12·15 | WP-02 | 마이그레이션, 미니 시드 |
| batch/, services/admin | COMP-13·14 | WP-07 | SyncJob 골격, 동기화 리포트 |
| infra/, CI | - | WP-01 | compose, GitHub Actions |

**의존 규칙(CI에서 검사)**

- 계층 계약: `api → services·pipeline → support → data` 방향으로만 import합니다. 아래 계층이 위 계층을 import하면 CI가 실패합니다.
- 독립 계약: services 아래 모듈끼리는 import하지 않습니다. RoutePlanner를 pipeline/에 두었으므로 admin과 course가 서로 부르지 않고 함께 씁니다(SDD 3.3의 유일한 예외가 없어짐).
- 금지 계약: batch는 api·services를 import하지 않습니다(ADR-012).
- SQL 위치: SQL 문자열은 data/repositories와 migrations에만 둡니다. 다른 폴더에서 `execute(`가 나오면 CI 검사에서 걸립니다.
- 외부 호출: httpx는 data/adapters와 data/ai_gateway에서만 import합니다.

## 5. 백엔드 구현

백엔드는 FastAPI 앱 하나와, 같은 코드를 다른 프로세스로 띄우는 배치로 만듭니다. API는 Pydantic 스키마를 먼저 합의하고, 프론트엔드는 그 스키마로 만든 가짜 응답으로 먼저 개발합니다.

| 영역 | 선택 | 이유 |
|---|---|---|
| 웹 프레임워크 | FastAPI, Pydantic v2, pydantic-settings | 입출력 검증과 OpenAPI 문서가 한꺼번에 나옴 |
| DB 접근 | psycopg 3(비동기) + psycopg_pool, pgvector 패키지 | SQL을 파일로 두고 바인딩 매개변수만 씀(ADR-010). ORM은 쓰지 않음 |
| 외부 호출 | httpx(비동기), 테스트는 respx | Gemini도 SDK 대신 REST로 불러 제한 시간을 호출마다 직접 정함 |
| 토큰·비밀번호 | PyJWT(HS256), argon2-cffi | NFR-011, FR-615 |
| 품질 도구 | ruff, pytest, pytest-asyncio, import-linter | 계획서 17.5 CI |
| 타입 공유 | openapi-typescript(프론트엔드가 실행) | 백엔드 스키마가 바뀌면 프론트엔드 빌드가 깨져서 바로 드러남 |

**요청 하나가 지나는 순서**

1. RequestLogger가 요청 ID를 붙이고, 끝날 때 PrivacyGuard.scrub()을 거친 레코드만 logs/*.jsonl에 씁니다.
2. SessionHeader가 X-Session-Id를 읽고, AI 요청(API-004·012·013)은 NoticeCheck가 X-Notice-Version을 확인합니다. 없으면 403(ERR-002)입니다.
3. RateLimiter가 세션당 AI 요청을 분당 5회로 막습니다. 워커가 1개라 메모리 토큰 버킷으로 충분합니다.
4. 라우터는 Pydantic으로 검증한 본문을 서비스에 넘기고, 서비스는 출처 ID(source_ids)가 담긴 결과만 돌려줍니다.
5. ResponseAssembler가 출처 카드와 ai_generated 표시를 붙입니다(ADR-014). 예외는 ErrorHandler가 `{error: {code, message, retry_after}}`로 바꿉니다.

**API 구현 순서(계획서 14.1 일정 안에서)**

| 주 | 기간 | API | 확인 방법 |
|---|---|---|---|
| 1주 | 10/27~11/2 | API-025 상태, API-007 선택 목록, API-005 근접 검색, API-006 촬영지 상세 | 미니 시드로 지도에 마커가 뜨면 통과 |
| 2주 | 11/3~11/9 | API-001~003 작품, API-019 출처, API-020~023 관리자 | 11/9 리뷰에서 C1·F2 시연(M3) |
| 3주 | 11/10~11/16 | API-013~015 AI 탐색, API-004 AI 소개, API-016·017 방문 인증 | 장애 주입 시 강등 응답 |
| 4주 | 11/17~11/23 | API-009~012 코스, API-018 배지, API-024 추천 코스 관리 | 11/23 리뷰에서 Must 시연(M4) |

API-008(구·군 통계)은 Should라 11/23 리뷰에서 착수 여부를 정합니다.

**AI가 아닌 핵심 로직**

| 클래스 | 구현 규칙 | 꼭 넣을 단위 테스트 |
|---|---|---|
| Geofence | 하버사인 거리 ≤ 인증 반경(기본 100m, 50~300m)이고 정확도 ≤ 50m일 때만 성공(BR-07) | 반경 99·100·101m, 정확도 50·51m, 인증 제외 장소 409 |
| TokenSigner | HS256, 클레임 {typ, loc, iat, kid}, 좌표·만료 없음, kid로 키 교체 | 변조 토큰 100건 거부(NFR-011), 이전 kid 토큰 확인 |
| TravelTimeEstimator | 도보 = 직선거리 × 1.3 ÷ 시속 4km. 도보가 1km를 넘으면 역 경유 시간과 비교해 짧은 쪽(BR-12) | 1km 경계, 같은 역이 최근접인 두 장소 |
| NearestNeighbor2Opt | 최근접 이웃으로 순서를 정한 뒤 개선이 없을 때까지 2-opt, 최대 16곳 | 8곳 이하에서 완전 탐색 대비 +10% 이내(AI-REQ-11) |
| BudgetFitter | 이동 + 체류 20분 × 장소 수가 예산을 넘거나 8곳을 넘으면 최저 점수 장소를 빼고 다시 계산, 3곳 미만이면 CourseInfeasible | 예산 1시간·8시간, 후보 3곳 |
| CandidateScorer | 취향 0.6 · 촬영 작품 수 0.2 · 거리 0.2 가중합, 상위 15곳(FR-309) | 가중치를 설정 파일로 바꾸면 순위가 바뀜 |
| ConditionRelaxer | 이동 제약 → 개봉연도 → 장르 → 구·군 순서로 하나씩 풀고 relaxed[]에 기록(FR-405) | 0건에서 몇 번째 완화에 결과가 나오는지 |
| WorkMatcher | 제목 유사도와 개봉연도로 점수, 0.9 이상 자동 연결·0.6 이상 검수 큐·그 아래 미매칭(BR-11) | 경계값 0.6·0.9, 부제·공백만 다른 제목 |
| PrivacyGuard | 전화번호·이메일·주민등록번호·카드번호 정규식 → 개인정보 | 가짜 개인정보 50건 100% 마스킹(NFR-003) |

## 6. AI 모듈 구현

기능 코드는 AI를 `LLMClient.generate(task, inputs, deadline)` 한 함수로만 부릅니다. 공급자 선택, 제한 시간, 재시도, 캐시, 호출 수 제한, 스키마 검증은 모두 게이트웨이(WP-06) 안에 둡니다. 실패하면 게이트웨이는 `AIUnavailable`을 던지고, 강등 처리는 부른 쪽이 합니다.

**작업 목록(프롬프트 7개 = 작업 7개)**

| 작업 | 쓰는 곳 | 입력 | 출력 스키마 | 상한 | 실패하면 |
|---|---|---|---|---|---|
| extract_query | F4 «2» | 마스킹한 질의, 허용 값 목록 | conditions.v1 | 3.0초 | 필터 패널을 열고 걸러낸 조건만 미리 채움(FR-411) |
| summarize_results | F4 «8» | 상위 10건 근거 묶음 | sentences.v1(3문장 이내) | 남은 시간 | 요약 없이 결과만 |
| structure_preference | F3 | 마스킹한 취향 문장, 허용 태그·장르 | preference.v1 | 3.0초 | 조건 직접 선택 화면(FR-312) |
| course_intro | F3 | 확정 코스(장소·순서·시간) | course_intro.v1 | 남은 시간 | 템플릿 문장 |
| work_intro | F1 | 스포일러 단계별 근거 묶음 | sentences.v1(300~500자) | 6.0초 | 원문 줄거리와 촬영지 목록 |
| suggest_tags | C1 배치 | 장소명·주소·설명, 허용 태그 | tags.v1 | 20초 | 제안 없이 검수 큐에 올림 |
| judge_match | C1 배치 | 촬영지 원본의 작품 + KMDb 후보 3개 | match.v1 | 20초 | 제안 없이 검수 큐에 올림 |

**시간 예산**

AI를 쓰는 API(API-004·012·013)는 요청을 받은 순간 마감 7.5초짜리 `Deadline`을 만들고 끝까지 넘깁니다. 호출 하나의 제한 시간은 `min(작업 상한, 남은 시간 − 0.3초)`이고, 이 값이 공급자 최소값(Gemini 1.0초, Ollama 2.0초)보다 작으면 부르지 않고 바로 강등합니다. 그래서 첫 공급자가 시간을 다 쓰고 실패해도 응답은 8초 안에 나갑니다.

*(그림: F4 요청 한 번의 시간 예산 · LLM 2회, 강등 2곳 — 원본 Claude Doc 참고)*

F1 작품 소개(상한 6.0초)와 F3 맞춤 코스(구조화 3.0초 + 소개 4.0초)도 같은 방식입니다. 남은 시간이 공급자 최소값(Gemini 1.0초)보다 짧으면 호출하지 않고 바로 강등합니다.

```python

```

**공급자 구현**

- GeminiProvider: Interactions API(`POST https://generativelanguage.googleapis.com/v1beta/interactions`)를 httpx로 부릅니다. JSON 출력은 `response_format: {type: "text", mime_type: "application/json", schema: …}`, 추론은 `generation_config.thinking_level: "minimal"`이고 결과는 `output_text`에서 읽습니다([Gemini 3 가이드](https://ai.google.dev/gemini-api/docs/gemini-3), [thinking 문서](https://ai.google.dev/gemini-api/docs/thinking)). 필드 이름은 구현 때 문서로 다시 확인하고, 바뀌어도 이 클래스 하나만 고칩니다.
- 모델은 `gemini-3.5-flash-lite`를 기본값으로, `gemini-3.1-flash-lite`를 대안으로 둡니다. 둘 다 무료 티어가 있고, 무료 티어 입력은 구글이 제품 개선에 쓸 수 있습니다([가격표](https://ai.google.dev/gemini-api/docs/pricing)). 분당·하루 한도 숫자는 AI Studio에서 확인해 설정에 넣습니다(확인 필요).
- Gemini 3 계열은 temperature를 기본값 1.0으로 둡니다. 낮추면 반복·품질 저하가 생길 수 있다고 권장하고 있어서, SDD 7.2의 '0~0.3'은 Ollama에만 적용합니다. 정확성은 스키마·허용 값·근거 대조로 지킵니다.
- OllamaProvider(선택): `POST /api/chat`에 `format`(JSON 스키마), `think: false`, `keep_alive: "30m"`, `options: {num_ctx: 8192, temperature: 0.2}`를 넣습니다. `OLLAMA_LLM_URL`이 비어 있으면 체인에서 빠집니다.
- OllamaEmbedder: `POST /api/embed`에 `{model: "bge-m3", input: [...]}`를 보내 1024차원 벡터를 받습니다. 제한 1.5초이고, 실패하면 사전 대조는 트라이그램만, 취향 유사도는 태그 일치만 씁니다.
- FakeProvider(테스트용): 정해진 JSON을 돌려주거나 시간 초과·429·5xx·스키마 위반을 냅니다. CI와 장애 주입 시험(NFR-002)은 이것만 씁니다.

**무료 한도 안에서 버티기**

- 분당 한도: 공급자별 토큰 버킷(rpm)을 두고, 자리가 없으면 마감 안에서만 기다립니다. 동시 10명이 몰려도 429를 받기 전에 서버가 먼저 줄을 세웁니다.
- 하루 한도: usage_counter에 `gemini:<모델>` 키로 호출마다 1씩 더합니다. 한도는 미국 태평양 시간 자정에 초기화되므로 날짜도 그 기준으로 자릅니다. 70%면 관리자 경고, 100%면 Gemini를 건너뜁니다(NFR-005).
- 캐시: 키는 SHA-256(작업 + 프롬프트 버전 + 마스킹한 입력 + 근거 해시), 24시간, 검증을 통과한 응답만 저장합니다(AI-REQ-15).
- 평가셋은 캐시를 끄고 돌리므로 한 번에 수백 회를 씁니다. 개발용 프로젝트 키로, 날을 나눠 돌립니다.

**출력 스키마 예: conditions.v1**

장르·구·군의 enum은 DB의 허용 값(API-007)으로 요청 때 채웁니다. 작품·인물·역 이름은 모델이 쓴 글자 그대로 받고, DictionaryResolver(«4»)가 표준 ID로 바꿉니다.

```json

```

preference.v1은 genres, mood_tags, works, persons, districts, start, budget_h(1~8), avoid를 같은 방식으로 정합니다. sentences.v1은 `{sentences: [{text, entities: []}]}`이고, 모델이 쓴 고유명사를 entities에 스스로 적게 합니다.

**프롬프트 파일(prompts/<작업>.v1.md) 구성**

1. 역할 한 줄: 작업마다 하나만(예: "부산 촬영지 검색 조건을 뽑는다").
2. 공통 규칙: 근거 묶음 안의 정보만 쓴다, 근거에 없으면 쓰지 않는다, 지정한 JSON만 출력한다, SQL·코드·명령을 만들지 않는다.
3. 허용 값과 근거 묶음(JSON, 항목마다 id·source_id).
4. 예시 2~3개(입력 → 출력 JSON). 예시는 평가셋 문항과 겹치지 않게 만듭니다.
5. 사용자 입력은 `<user_input>…</user_input>` 안에만 넣고, 그 안의 지시는 따르지 않는다고 적습니다(AI-REQ-09).

**근거 대조와 마스킹**

- GroundingVerifier.gate(): 근거 묶음이 비면 LLM을 부르지 않습니다.
- GroundingVerifier.verify(): 문장마다 EntityLexicon(DB의 작품·인물·장소·구·군 이름)과 정규식(연도, 분·시간, m·km)으로 찾은 항목과 모델이 적은 entities가 모두 근거에 있는지 봅니다. 하나라도 없거나 PhraseFilter(결말·반전 표현 목록)에 걸리면 그 문장을 지웁니다.
- F1은 남은 문장이 2개 미만이면 원문으로 강등하고, F3·F4는 지워진 문장만 빼고 보여 줍니다.
- PrivacyGuard.mask(): 전화번호, 이메일, 주민등록번호, 카드번호를 `[개인정보]`로 바꾸고 종류만 기록합니다. 좌표는 프롬프트에 넣지 않고 '현재 위치' 표지나 구·군 이름만 넣습니다(BR-10).

**config/ai.yaml 초기값**

```yaml

```

## 7. DB 구현

SDD 5.2의 테이블 16개를 만들고, 아래 표의 차이만 둡니다. 이 장의 DDL·검색 SQL·사전 대조 쿼리는 PostgreSQL 16.15와 pgvector 0.6 위에서 psycopg 3.3으로 실제로 돌려 확인했습니다. 전체 파일은 프로젝트 파일 `busan-cineloca/starter/`(마이그레이션 3개, 템플릿 SQL 5개, 테스트용 가짜 데이터와 확인 스크립트)에 있으니 WP-02는 이걸 복사해서 시작합니다.

**마이그레이션 규칙**

- `backend/migrations/NNN_<이름>.sql`을 번호순으로 실행하고 적용한 번호를 `schema_migrations`에 남기는 작은 러너(`python -m app.data.migrate`)를 씁니다. ORM과 Alembic은 쓰지 않습니다.
- 001_extensions(vector, pg_trgm, cube, earthdistance) → 002_core(테이블 16개) → 003_indexes(SDD 5.1 색인과 shooting.location_id) 순서입니다. 머지한 파일은 고치지 않고 새 번호를 추가합니다.
- DB 로캘은 이미지 기본값을 그대로 둡니다. `C` 로캘로 만들면 pg_trgm이 한글에서 트라이그램을 하나도 뽑지 못해 퍼지 매칭이 전부 0점이 됩니다(C와 C.UTF-8로 비교 확인). 마이그레이션 테스트에 `SELECT show_trgm('마동석') <> '{}'` 확인을 넣습니다.

**SDD 5.2와 다르게 만드는 곳**

| 테이블.열 | 바꾼 점 | 이유 |
|---|---|---|
| location.ext_key, work.ext_key | 새 열, UNIQUE | 동기화해도 id가 유지돼야 스탬프 토큰(loc), 즐겨찾기, 저장 코스, 검수 항목이 깨지지 않고, 관리자가 편집한 값도 보존할 수 있음 |
| location.retired, work.retired | 새 열 | 원본에서 사라진 행은 지우지 않고 숨김(같은 이유) |
| location.address, gu | NULL 허용 | 「영화 속 부산정보」에는 주소가 없는 레코드가 있음(계획서 2장). 좌표가 없으면 목록에만 나옴 |
| course_stop.leg_mode | VARCHAR(4) → VARCHAR(6) | 'subway'가 들어가지 않음 |
| work.genres, location.caution | NOT NULL, 기본값 '{}'·'none' | 템플릿 조건을 단순하게 |

**핵심 DDL(촬영지)**

```sql

```

**검색 템플릿 T1~T4**

조건에 따라 템플릿 하나를 고릅니다. 네 파일은 공통 CTE `matched`(작품·인물·장르·구·군·연도 조건을 통과하고 retired가 아닌 촬영지–작품 쌍)를 같이 씁니다. SQL 파일은 앱 시작 때 한 번 읽어 상수로 두고, 값은 모두 바인딩 매개변수로 넣고, 정렬과 개수는 허용 목록에서만 고릅니다(ADR-010).

| 조건 | 템플릿 | 핵심 조건 |
|---|---|---|
| 기준 위치나 이동 조건이 없음 | T1_FILTER | 일치한 작품 수 순 |
| 현재 위치·장소·특정 역에서 걸어서 N분, 지도 반경 | T2_NEAR_POINT | 반경(m) = N × 4000/60 ÷ 1.3(5장 도보 규칙). earth_box로 GiST 색인을 타고 earth_distance로 다시 자름 |
| 역 지정 없이 '역에서 걸어서 N분' | T3_NEAR_STATION | station_walk_min ≤ N |
| 'X역에서 지하철로 N분' | T3_NEAR_STATION | station_time(X → 최근접 역) + station_walk_min ≤ N |
| 결과 유형이 작품 | T4_WORKS | 촬영지 수 순 |

conditions.v1에서 base.kind가 station이고 name이 비어 있으면 '아무 역'으로 읽습니다. 시연 질의 '마동석 나온 영화 촬영지 중 지하철역에서 걸어서 10분 안'은 인물 조건 + T3(minutes 10)이 됩니다.

```sql

```

`matched` 안의 조건은 `(%(gus)s::text[] IS NULL OR l.gu = ANY(%(gus)s::text[]))` 꼴입니다. 서비스는 '조건 없음'을 빈 목록이 아니라 None으로 넘깁니다. 결과의 source_ids에 좌표 출처(DATA-06)와, 역을 썼다면 역 출처(DATA-08)를 서비스가 더해 출처 카드를 만듭니다.

**psycopg에서 걸리기 쉬운 것(직접 확인)**

- 같은 `%(이름)s`를 여러 번 써도 됩니다. None이 들어갈 수 있는 자리에는 `::int[]`처럼 형을 붙여야 합니다.
- 벡터를 파이썬 list로 넘기면 `double precision[]`이 되어 `<=>`에서 "operator does not exist" 오류가 납니다. SQL에 `%(vec)s::vector`라고 쓰거나 `pgvector.Vector`로 감쌉니다. INSERT는 list로도 통과해서 검색할 때 처음 터집니다.
- pg_trgm의 `%` 연산자는 psycopg 자리표시자와 겹치므로 `%%`로 씁니다. 사전은 수천 행이라 `ORDER BY similarity(surface, %(q)s) DESC LIMIT 3`으로 충분합니다.

**사전 대조에서 잰 값**

저장할 때와 질의할 때 같은 정규화(NFKC, 소문자, 공백·기호 제거)를 해야 합니다. '마 동석'은 정규화하면 1.0이지만 그대로 두면 0.29입니다. 세 글자 이름의 한 글자 오타('마동숙', '해운데')는 0.33이라 SDD 기준 0.35를 넘지 못합니다. 그래서 임베딩 보완(코사인 0.75)이 실제로 동작해야 하고, 평가셋에도 이런 문항을 넣습니다. '범죄도시 2'와 '범죄도시'는 0.57입니다.

**동기화 반영(publish) 규칙**

- 배치는 `stg` 스키마에 같은 구조로 적재하고, CountGuardStep을 통과하면 한 트랜잭션에서 public에 반영합니다.
- 촬영지와 작품은 ext_key로 UPSERT해 id를 유지합니다. 이때 tags(검수 승인으로만 바뀜), caution, safety_note, cert_radius_m, cert_excluded, 그리고 geocode_status가 manual인 행의 lat·lon은 덮어쓰지 않습니다.
- stg에 없는 행은 retired로 표시합니다. shooting, photo, work_person은 ext_key로 id를 맞춘 뒤 지우고 다시 넣습니다.
- 꼭 넣을 테스트: 같은 원본으로 두 번 동기화해도 id와 관리자 편집 값이 그대로여야 합니다.

**좌표 받기와 변환**

공공데이터포털의 주소 검색 API(15057017) 출력 항목에는 좌표가 없습니다(포털 명세 확인). 그래서 계획서 DATA-06대로 좌표 제공 API를 따로 불러야 하고, 키도 따로 받아야 할 수 있습니다. 이 좌표(entX, entY)는 UTM-K(EPSG:5179)로 알려져 있어서 pyproj로 바꾸고, 첫 호출 때 부산시청 주소로 확인합니다. UTM-K 값이 x 약 1,143,000, y 약 1,688,000 근처면 맞습니다(pyproj 왕복 변환으로 계산).

```python

```

**시드 데이터**

- 미니 시드 `infra/seed/mini_seed.sql`(WP-02, 1주차): 실제 원본 응답에서 고른 촬영지 20곳과 작품 10편입니다. 해운대·광안리·서면·부산역·영도 주변에서 시연 장면 5개가 모두 결과를 내도록 고르고, 좌표는 주소 API로 받아 넣고, source_id를 채웁니다. 임베딩은 비어 있어도 됩니다(강등 경로를 그대로 탐). C1 배치가 나오기 전까지 프론트엔드, F2, F4는 이것으로 개발합니다.
- 전체 시드 `seed.sql.gz`(C1 이후): `pg_dump --no-owner --exclude-table-data=ai_cache --exclude-table-data=usage_counter --exclude-table-data=sync_run | gzip`으로 만들고 `gunzip -c seed.sql.gz | psql`로 복원합니다. ll_to_earth 식 색인까지 PG16에서 그대로 복원되는 것을 확인했습니다. 시드는 GitHub Release에 올리고 저장소에는 넣지 않습니다.
- 시연 질의가 실제 데이터에서 결과를 내는지는 시드를 만든 날 바로 확인합니다. 결과가 없으면 질의를 데이터에 맞게 바꿉니다.

## 8. 프론트엔드 구현

React + Vite + TypeScript SPA입니다. 폭 360px 모바일을 먼저 만들고, 사용자 화면은 하단 탭 5개(지도·작품·AI 탐색·코스·내 기록), 관리자 화면은 /admin 데스크톱 레이아웃을 씁니다. 백엔드보다 먼저 움직일 수 있도록 MSW 목 응답으로 시작하고, OpenAPI 타입이 나오면 실제 API로 바꿉니다.

**라이브러리**: react-router(라우팅), TanStack Query(서버 상태와 캐시), openapi-typescript(API 타입 생성), MSW(목), Playwright(E2E)만 씁니다. 전역 상태 라이브러리는 없이 localStorage 훅으로 충분합니다. 버전은 작업 시작 때의 안정 버전으로 고정하고 package-lock.json을 커밋합니다.

**라우트와 화면**

| 경로 | 화면 | 부르는 API | 메모 |
|---|---|---|---|
| / | UI-01 지도 홈 | 005, 007 | GeoProbe 5초, 실패하면 부산역 기준. 반경 500m·1km·3km |
| /locations/:id | UI-02 촬영지 상세 | 006, 016 | 방문 인증, 길찾기 링크, 관람 주의 안내 |
| /works | UI-03 작품 목록 | 001 | 검색·장르·정렬, 페이지 버튼 |
| /works/:id | UI-04 작품 상세·AI 소개 | 002, 003, 004 | 스포일러 단계, 'AI 생성' 표시, KOBIS는 따로 늦게 뜨어도 됨 |
| /ask | UI-05 AI 탐색 | 013, 014, 015, 007 | 조건 칩, 선택지, 강등되면 FilterPanel |
| /courses | UI-06 코스 | 009, 011, 012 | 추천·나만의·AI 맞춤 탭 |
| /courses/:id, /courses/view | UI-07 코스 상세 | 010, 018 | 계산 결과는 라우터 state로 넘기고, 저장하면 cl.courses에 넣음 |
| /me | UI-08 내 기록 | 017 | 서명이 유효한 토큰만 표시, 저장 위치 고지(FR-509) |
| /sources | UI-09 데이터 출처·이용 안내 | 019 | KOBIS 문구 포함(FR-705) |
| /admin/login, /admin/sync | UI-10 동기화 리포트 | 020, 021 | 5회 실패하면 423 |
| /admin/reviews | UI-11 검수 큐 | 022, 023 | 촬영지 속성 편집을 같은 화면에 |
| /admin/courses | UI-12 추천 코스 관리 | 024 | UI-11과 같은 레이아웃 |

**공통 모듈(SDD COMP-01 이름 그대로)**

- ApiClient: openapi-typescript로 만든 타입과 얇은 fetch 래퍼입니다. 모든 요청에 X-Session-Id(탭마다 `crypto.randomUUID()`로 만들어 sessionStorage에 둠)를, AI 요청(API-004·012·013)에는 X-Notice-Version을 붙입니다. 403 ERR-002가 오면 NoticeGate를 다시 띄웁니다. 오류 문구는 ERR 코드별로 errors.ts 한 곳에 둡니다.
- GeoProbe: `getCurrentPosition({enableHighAccuracy: true, timeout: 5000, maximumAge: 0})`. 지도 홈에서는 거부·실패·5초 초과면 API-007의 부산역을 기준으로 씁니다(FR-201). 인증에서는 정확도가 50m를 넘으면 실외에서 다시 하라고 안내합니다(FR-503). 좌표는 메모리에만 두고 localStorage, 콘솔 로그, 분석 도구에 넣지 않습니다.
- MapView: 카카오 SDK를 `https://dapi.kakao.com/v2/maps/sdk.js?appkey=<키>&autoload=false&libraries=clusterer`로 한 번만 불러오고 `kakao.maps.load()` 뒤에 그립니다. 마커 묶음은 MarkerClusterer입니다. SDK 로드에 실패하면(도메인 미등록 등) 목록만 보여 주는 모드로 바뀝니다(SRS D2). 카카오 로고와 저작권 표시는 가리지 않고(FR-706), 카카오 응답은 화면에만 쓰고 저장·캐시하지 않습니다.
- 길찾기(FR-208): `https://map.kakao.com/link/to/<이름>,<lat>,<lon>`을 새 창으로 엽니다.
- NoticeGate: 첫 방문 모달(외부 AI 전송 가능성, 위치 미저장)을 띄우고, 확인하면 cl.notice에 버전을 적습니다. 확인 전에는 AI 입력창을 막습니다(FR-701).
- AiLabel: AI 문장에 'AI 생성'을, degraded·fallback이면 '기본 정보로 대체됨'을 붙입니다(FR-707). 마스킹된 요청이면(masked) 그 사실도 보여 줍니다(FR-702).
- SourceCard: 앱 시작 때 API-019 출처 대장을 한 번 받아 두고, 응답의 source_ids를 기관·데이터명·기준일·링크로 바꿔 표시합니다. 외부 데이터나 AI 문장이 나오는 영역에는 빠짐없이 붙입니다(NFR-008).
- ConditionChips: API-013의 chips를 보여 주고, 칩을 지우면 그 조건을 빼고 API-014로 다시 검색합니다. choices가 있으면(NEEDS_CHOICE) 하나를 고르게 합니다.
- FilterPanel: API-007 선택 목록으로 만들고, AI가 강등되면 응답의 prefill로 채워서 엽니다(FR-411).
- 방문 인증 흐름: GeoProbe(고정밀) → API-016에 location_id, 좌표, accuracy_m, 그리고 이 브라우저가 가진 스탬프 토큰(held, 중복 판정용)을 보냅니다. 성공하면 토큰을 cl.stamps에 넣고, 실패하면 reason과 distance_m으로 안내합니다.

**브라우저 저장(localStorage)**

| 키 | 내용 | 규칙 |
|---|---|---|
| cl.stamps | 스탬프 토큰 배열 | 서버가 준 토큰만. 화면에는 API-017로 서명을 확인한 것만 |
| cl.badges | 배지 토큰 배열 | 위와 같음 |
| cl.courses | 저장 코스 | 최대 10개, 넘으면 저장을 막고 안내(FR-306) |
| cl.favorites | 즐겨찾기 id | Should(FR-801)이라 키만 마련 |
| cl.notice | 확인한 이용 안내 버전 | 서버 버전과 다르면 다시 안내 |

읽기와 쓰기는 모두 try/catch로 감싸고(사파리 사생활 보호 모드 등), 깨진 JSON은 버리고 빈 값으로 시작합니다.

**목과 타입**

- 1주차에 `frontend/src/mocks/handlers.ts`에 API-001·002·005·006·007 목을 미니 시드와 같은 데이터로 만듭니다. `VITE_USE_MOCKS=1`일 때만 켭니다. AI API 목에는 강등 응답도 넣어 화면의 강등 처리를 먼저 만듭니다.
- 백엔드가 /openapi.json을 내면 `npx openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.d.ts`로 타입을 만듭니다. CI에서 다시 만든 결과가 커밋된 파일과 다르면 실패하게 해서 API 계약이 깨지는 것을 막습니다.

**개발 서버와 배포**

- 개발: `npm run dev`(5173)에서 vite.config의 server.proxy로 `/api`를 `http://localhost:8000`으로 넘깁니다. 휴대폰으로 확인할 때는 Tailscale 주소를 씁니다. HTTPS가 아니면 휴대폰에서 위치 권한이 뜨지 않습니다.
- 배포: `npm run build` 결과를 web 이미지(nginx)에 넣고, nginx가 /api를 api:8000으로 넘깁니다. SPA 경로는 `try_files $uri /index.html`로 처리합니다.
- 카카오 JS 키는 번들에 들어가므로 비밀이 아닙니다. 대신 카카오 개발자 콘솔에 사이트 도메인 3개(localhost:5173, localhost:8080, ts.net 주소)만 등록합니다.

**화면 공통 규칙**

- 폭 360·768·1440px에서 가로 스크롤이 없고, Chrome·Edge·iOS Safari 최신 2개 버전에서 동작합니다(NFR-004).
- AI 요청 중에는 버튼을 막고 진행 표시를 띄웁니다. 서버가 7.5초 안에 강등 응답까지 돌려주므로, 클라이언트 제한 시간은 안전용으로 10초만 둡니다.
- 입력 200자 제한은 화면에서도 막습니다(서버도 검증).

## 9. 테스트와 AI 평가

CI는 실제 외부 API와 실제 LLM을 부르지 않습니다. 실제 Gemini는 평가셋을 돌릴 때만 개발용 키로 부릅니다. 테스트를 통과하지 못한 코드는 main에 들어가지 않고, 통과시키려고 테스트를 지우거나 건너뛰지 않습니다.

**층별 테스트**

| 층 | 도구 | 대상 | 기준 |
|---|---|---|---|
| 단위 | pytest, vitest | 5장 핵심 로직 표의 클래스, GroundingVerifier, PhraseFilter, SchemaValidator, ProviderChain | 핵심 모듈 라인 커버리지 70%(NFR-016) |
| 통합(DB) | pytest + 실제 PostgreSQL(CI 서비스 컨테이너, pgvector 이미지) | 마이그레이션, 템플릿 SQL, Repository, publish | 템플릿마다 픽스처 결과를 고정(7장 starter의 확인 스크립트를 pytest로 옮김) |
| 통합(API) | pytest + httpx AsyncClient | 라우터 25개의 입력 검증, ERR 코드, 헤더 규칙 | 상태 코드와 응답 스키마 |
| 어댑터 | respx | BaseApiClient 하위 6개(재시도 3회, 하루 한도 80%, parse) | 저장 가능한 실제 응답 사본은 fixtures/real/, 저장 금지 데이터는 손으로 만든 fixtures/fake/ |
| E2E | Playwright | 시연 장면 5개와 AI 장애 때의 강등 화면 | 360px·1440px. 위치는 `context.setGeolocation()`으로 넣음 |
| 부하 | Locust | 동시 10명 | NFR-001 p95 2초, NFR-006 p95 8초 |
| 장애 주입 | FakeProvider | 시간 초과, 429, 5xx, 스키마 위반 각 10회 | AI 기능은 전부 강등 응답, 지도·필터·인증·상세는 정상(NFR-002) |

**가짜 공급자와 픽스처**

- `AI_PROVIDERS=fake`이면 FakeProvider가 작업별 고정 JSON을 돌려줍니다. `FAKE_AI_MODE=timeout|429|500|bad_schema`로 장애를 냅니다. E2E와 장애 주입은 이 설정으로 돌립니다.
- FakeEmbedder는 텍스트 해시를 씨앗으로 한 1024차원 벡터를 만들어 결과가 매번 같게 합니다.
- 가짜 개인정보 50건(전화번호·이메일·주민등록번호·카드번호 형식)은 `tests/fixtures/pii.json`에 둡니다. 실제 사람의 정보는 쓰지 않습니다.
- 위치 미저장 감사(NFR-003): E2E가 위치를 쓰는 요청을 100회 보낸 뒤 DB 덤프와 logs/에서 그 좌표 문자열을 검색해 0건이어야 합니다.

**AI 평가셋(eval/)**

| 세트 | 문항 | 항목 형식 | 통과 기준 |
|---|---|---|---|
| f4_queries.json | 60 | text, expected_conditions, expected_ids | 필드 일치 90%, 정밀도 85%, 재현율 80%, 결과 밖 사실 0건(AI-REQ-10) |
| f3_preferences.json | 30 | text, start, budget_h, expected_preference | 구조화 일치 85%, 예산 준수 100%, 8곳 이하에서 최적해 대비 +10% 이내(AI-REQ-11) |
| f1_works.json | 30편 × 스포일러 2단계 | work_id, spoiler | 사실 불일치 0건, '없음' 단계 스포일러 0건(AI-REQ-12) |
| redteam.json | 30 | text, expect(out_of_scope, ignore_injection, masked) | 올바른 처리 100%(AI-REQ-09, NFR-010) |
| 매칭 표본 | 무작위 50건 | 사람이 확인 | 매칭 정확도 95%(AI-REQ-13) |

- 실행: `python -m eval.run --set f4 --provider gemini --no-cache`. 결과는 `eval/results/<날짜>_<프롬프트 버전>.json`에 남기고, 프롬프트·모델·스키마를 바꾸는 PR에는 결과 요약을 붙입니다(AI-REQ-14).
- 호출 수는 대략 f4 120회(추출 + 요약), f3 60회, f1 60회, 레드팀 30~60회입니다. 무료 한도 안에서 하루 한두 세트씩 나눠 돌립니다.
- 문항 초안은 AI가 만들어도 되지만, 기대값(expected_ids 등)은 사람이 DB에서 확인해 확정합니다. 프롬프트 예시와 겹치는 문항은 빼니다.
- '결과 밖 사실 0건'은 GroundingVerifier가 자기 자신을 채점하는 꼴이 되지 않게, 자동 대조에 더해 결과의 20%를 사람이 읽고 확인합니다.

**CI(GitHub Actions, PR마다)**

```bash

```

E2E는 시간이 걸리므로 main 앞 통합 브랜치(또는 매일 밤)에서 `AI_PROVIDERS=fake`로 compose를 띄우고 `npx playwright test`를 돌립니다.

**부하 시험 주의**

NFR-001은 Locust 10명으로 3분 돌리면 됩니다. NFR-006(실제 AI p95 8초)은 무료 티어의 분당 한도 때문에 동시 10명이 길게 못 버티므로, 요청 30건 정도로 짧게 재고 한도를 넘는 부분이 대기열과 강등으로 처리되는지를 함께 봅니다.

## 10. 작업 패키지와 순서

작업을 12개 패키지(WP)로 나눌습니다. 패키지 하나는 워커 하나가 맡고, 4장 표의 폴더만 고칩니다. 주차는 A(10/27~11/2), B(11/3~11/9, 스프린트 1 리뷰), C(11/10~11/16), D(11/17~11/23, 스프린트 2 리뷰), E(11/24~11/29, 11/26 MVP)입니다.

| WP | 맡는 것 | 먼저 끝나야 하는 것 | 끝났다고 보는 기준 | 주차 |
|---|---|---|---|---|
| WP-01 기반 | 저장소 골격, compose 5개 서비스, nginx, .env.example, CI, 공통 미들웨어(5장 요청 순서), API-025 | 없음 | `docker compose up` 뒤 /api/health 200, CI의 ruff·pytest·lint-imports·gitleaks가 도는 상태 | A 앞쪽 2일 |
| WP-02 DB·저장소 계층 | 마이그레이션(starter), Repository 10종, SearchTemplates, SourceRegistry, 미니 시드, 시드 내보내기·적재 명령 | WP-01 | 템플릿 통합 테스트 통과, 미니 시드로 시연 장면 1·3·5의 검색이 결과를 냄 | A |
| WP-03 지도 API(F2) | API-005·006·007, MapService, TravelTimeEstimator | WP-02 | 반경 500m·1km·3km와 필터 테스트, 동시 10명 p95 2초 | A~B |
| WP-04 프론트 골격·지도 화면 | 하단 탭, ApiClient, GeoProbe, MapView, NoticeGate, SourceCard, AiLabel, MSW, UI-01·02·09 | WP-01(처음엔 목으로) | 휴대폰(Tailscale)에서 지도 홈 → 상세 → 길찾기, 360px에서 가로 스크롤 없음 | A~B |
| WP-05 외부 데이터 어댑터 | BaseApiClient와 하위 6개, PolicyGuard, 좌표 변환 | WP-01 | 어댑터별 respx 테스트, 실제 키로 최소 1회 수집, 저장 정책 검사 통과 | A~B |
| WP-06 AI 게이트웨이·안전 | LLMClient, ProviderChain, CircuitBreaker, PromptRegistry, SchemaValidator, 캐시·호출 수, Embedder, FakeProvider, PrivacyGuard, GroundingVerifier, PhraseFilter | WP-02 | 장애 4종 단위 테스트, 7.5초 마감 테스트, 개발 키로 Gemini 실호출 1회 성공 | B |
| WP-07 C1 배치·관리자 | SyncJob 11단계, publish, AdminService, API-020~023, UI-10·11 | WP-02, WP-05, 태그 제안은 WP-06 | 실제 원본으로 동기화 → 건수 가드 통과 → seed.sql.gz 배포. 두 번 돌려도 id 유지 | A~C(임계 경로) |
| WP-08 F1 작품 | API-001~004, ArchiveService, work_intro, UI-03·04 | WP-02, AI 소개는 WP-06 | 시연 장면 2 통과, 스포일러 2단계·근거 대조 강등 테스트, F1 평가 목표. 목록·상세는 B주, AI 소개는 C주에 끝냄 | B~C |
| WP-09 F4 AI 탐색 | QueryPipeline 9단계, API-013~015, UI-05, FilterPanel | WP-02, WP-06 | 시연 장면 3 통과, AI 장애 때 prefill된 필터 패널, F4 평가 목표 | C~D |
| WP-10 F3 코스 | RoutePlanner, BudgetFitter, CandidateScorer, API-009~012·024, UI-06·07·12 | WP-02, WP-06 | 시연 장면 4 통과, 최적해 대비 +10%, F3 평가 목표 | C~D |
| WP-11 F5 방문 인증 | Geofence, TokenSigner, API-016~018, UI-08, 인증 버튼 | WP-02, WP-04 | 경계값 테스트, 변조 토큰 100건 거부, 위치 미저장 감사 | C |
| WP-12 평가·통합·시연 | eval/ 세트 4개, E2E 5장면, Locust, 장애 주입, 리허설, 백업 영상 | 평가셋 작성은 바로, 실행은 WP-08~10 | AI-REQ-09~13 결과 기록, NFR-001·002·006 측정, 리허설 2회 | B~E |

*(그림: 작업 패키지 12개의 주차 · A~E주, 점선은 스프린트 1 리뷰와 MVP — 원본 Claude Doc 참고)*

WP-07이 C주까지 이어지므로 F1·F3·F4는 미니 시드로 먼저 만들고, seed.sql.gz가 나오면 실제 데이터로 다시 확인합니다.

C2(개인정보·출처)는 패키지 하나가 아니라 WP-01(NoticeCheck), WP-02(SourceRegistry), WP-04(SourceCard·NoticeGate·AiLabel·UI-09), WP-05(PolicyGuard), WP-06(PrivacyGuard)에 나뉘어 있습니다. 다 모인 뒤 WP-12가 NFR-003·007·008 검사로 한 번에 확인합니다.

**병렬로 돌리는 법**

- A주 앞쪽 2일은 WP-01만 합니다. 구조가 서야 다른 워커가 같은 파일을 동시에 만들지 않습니다.
- 그 뒤에는 WP-02, WP-04, WP-05, WP-07을 동시에 시작합니다. WP-04는 MSW 목으로, WP-07은 WP-05의 저장된 실제 응답으로 시작합니다.
- WP-06은 B주에 끝내야 C주에 F1·F3·F4가 프롬프트만 더하면 됩니다. 가장 먼저 쓰는 곳은 WP-07의 suggest_tags입니다.
- WP-12의 평가셋 문항은 B주부터 씁니다. 기대값을 실제 데이터로 확인해야 하므로 seed.sql.gz가 나오면 한 번 더 맞춥니다.
- 일정이 밀리면 2장 표의 ①~⑤ 순서로 줄입니다. F4와 C2는 줄이지 않습니다.

**워커에게 주는 작업 지시 형식**

AI 코딩 에이전트에게 일을 맡길 때는 아래 형식으로 한 번에 하나의 WP 안에서 하루 분량 이하만 줍니다.

```text

```

## 11. 구현하며 걸리기 쉬운 것

계획서 리스크 표(RK1~15)에 없거나, 실제로 만들 때 더 커지는 것만 모았습니다.

| 함정 | 어떻게 드러나나 | 미리 할 일 | WP |
|---|---|---|---|
| 키 발급이 늦음 | 수집·AI 개발이 키를 기다림 | A주 첫날에 모두 신청: 공공데이터포털(데이터셋마다 활용 신청), KMDb, KOBIS, 좌표 API, TourAPI, 카카오, Gemini 프로젝트 2개(개발·시연). 키가 오기 전에는 픽스처로 개발 | 05 |
| KMDb 저장 범위(TBD-01) | 약관이 장르·인물까지 저장 금지면 F4 인물 조건과 시연 장면 3이 깨짐. 이 문서는 'ID_ONLY면 kmdb 열만 비운다'로 읽었음 | A주 안에 약관 원문을 확인하고, 다르면 팀이 바로 정함 | 05·07 |
| 좌표 확보 | 주소 없는 레코드, 별도 좌표 API, UTM-K. 확보율이 85% 아래로 떨어짐(RK4) | 7장대로 변환하고 부산시청으로 검증. 나머지는 관리자가 수동 보정(manual) | 05·07 |
| 시연 질의와 데이터가 안 맞음 | 마동석 출연작의 부산 촬영지가 없으면 장면 3이 0건 | 미니 시드를 만들 때 확인하고, 없으면 데이터에 있는 배우로 질의를 바꿈 | 02·12 |
| 카카오 지도가 안 뜨 | 도메인 미등록, JavaScript 키 대신 REST 키 사용, 앱의 카카오맵 사용 설정 | 도메인 3개 등록, 콘솔 사용 설정 확인, SDK가 실패해도 목록 모드로 버티게 | 04 |
| Gemini 429·모델 변경 | 무료 한도 초과, 미리보기 모델 종료 | 정식 모델만 씁니다. 시연 주 월요일에 AI Studio에서 모델과 한도를 다시 확인합니다. 시연 당일 아침에 리허설하면 같은 질의는 24시간 캐시에서 나옵니다. 실시간 호출을 보여 줄 질의는 따로 하나 준비합니다 | 06·12 |
| CPU 임베딩 속도 | 질의 임베딩이 1.5초를 넘으면 매번 트라이그램만 동작 | A·B주에 시연 노트북에서 실측. 배치 임베딩은 느려도 됨 | 06 |
| 시연 GPS | 휴대폰은 위치를 모의하기 어렵고, 실내에서는 정확도가 50m를 넘음 | 인증 장면은 노트북 Chrome 개발자 도구의 Sensors에 촬영지 좌표를 넣어 시연(계획서 RK11). E2E도 같은 방식 | 11·12 |
| 학교 네트워크 | Tailscale이 릴레이로 돌아 느려지거나 인터넷이 끊김 | 휴대폰 핫스팟 예비, 발표 전날 백업 영상 | 12 |
| 동기화마다 id가 바뀜 | 스탬프·저장 코스·검수 항목이 엉뚱한 곳을 가리킴 | 7장 ext_key 규칙과 두 번 동기화 테스트 | 07 |
| 한글 퍼지 매칭 0점 | DB를 C 로캘로 만들면 트라이그램이 비어 사전 대조가 전부 실패 | 7장 확인 쿼리를 마이그레이션 테스트에 | 02 |
| AI 워커가 자주 하는 실수 | 공공 API 응답 필드를 짐작으로 씀, 구현을 따라 쓴 테스트, 실패 테스트를 skip, 라이선스 확인 없는 의존성 | 실제 응답 사본을 먼저 넣고, 12장 규칙을 지키고, 리뷰는 테스트부터 읽음 | 전체 |

## 12. 워커 공통 규칙

아래 내용을 저장소 루트의 AGENTS.md로 넣습니다. 사람 워커도 같은 규칙을 따릅니다. 이 문서는 Markdown으로 내보내 docs/build-plan.md로, SDD는 docs/sdd.md로 넣어 두면 워커가 저장소 안에서 바로 읽을 수 있습니다.

```markdown

```

**SDD와 다르게 만드는 것(docs/deviations.md 초깃값)**

| 항목 | SDD v0.1 | 이 문서 | 장 |
|---|---|---|---|
| 대체 체인 | Gemini → Ollama → 강등 | Gemini → 강등, Ollama는 설정으로 켬 | 1·6 |
| AI 제한 시간 | 조건 추출·구조화 10초, 요약·소개 8초(SRS FR-411·IF-09도 10초) | 요청 마감 7.5초 안에서 작업별 상한 | 6 |
| temperature | 0~0.3 | Gemini는 기본값 1.0, Ollama만 0.2 | 6 |
| 배치 환경 | 팀 서버 GPU, Cloudflare 터널, 컨테이너 6개 | 발표자 노트북, Tailscale serve, web·api·db·embed + batch 프로필 | 3 |
| 임베딩 | 팀 서버에서만 계산 | 아무 PC의 Ollama CPU, 실패하면 트라이그램만 | 1·6 |
| 폴더 | 계획서 17.2의 batch/ 최상위 | backend/app/batch, 어댑터는 data/ 아래 | 4 |
| DB | 5.2 정의 | ext_key·retired 추가, address·gu NULL 허용, leg_mode VARCHAR(6) | 7 |
| 시연 질의 문구 | 계획서 20.3 '지하철 10분 안' | SRS AC-05 '지하철역에서 걸어서 10분 안' | 2·7 |
| 용어 | 작품지·촬영지 혼용 | 촬영지(코드는 location) | 1 |

