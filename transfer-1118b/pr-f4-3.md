#PREV_PR 위에 쌓인 PR입니다

## 관련 이슈
Closes #F4_ISSUE

## 관련 요구사항·설계 ID
API-013·014·015, FR-401~412, FR-702·707, AI-REQ-15, ERR-011·015, BR-10, COMP-02·06

## 변경 내용
- `POST /api/query`(질의), `POST /api/query/choose`(후보 고르기), `POST /api/query/chips/remove`(조건 칩 지우기), `DELETE /api/query/session`(새 대화, 204)
- `POST /api/search`: AI 없이 필터 패널 조건으로 검색하고 결과가 없으면 조건을 차례로 풂(`FilterSearchService`)
- QueryService에 실제 LLMClient(환경변수, 호출 수·캐시는 DB), DictionaryResolver, TemplateSearcher 연결. 세션이 메모리에 있어 프로세스에 하나만 둠
- 세션 ID는 `X-Session-Id` 헤더로 받고 응답 `session_id`로 돌려줌. 기준 위치 좌표는 요청 본문 `base`로만 받고 응답·로그에 남기지 않음
- 오류: 400 INVALID_QUERY(빈 질문·200자 초과·고를 항목 없음), 429 RATE_LIMITED + Retry-After, 503 DB_UNAVAILABLE. AI 장애는 200에 `status=ai_unavailable`과 `filter_panel`
- SDD와 다른 점: ① 고르기·칩 지우기 경로 추가 ② 응답 필드는 QueryResult 이름 그대로(items → `hits`, prefill → `filter_panel`, summary는 문장 목록) ③ 200자 초과는 422가 아니라 400 ④ 결과 유형 work는 촬영지로 돌려줌
- 남은 것: `X-Notice-Version` 확인(FR-701), 출처 카드 조립, 프론트 AskPage와 API 타입
- 400줄을 넘음(687줄, 테스트 292줄)

## 테스트 방법과 결과
- `ruff format --check .`, `ruff check .` 통과
- `python -m pytest -q` → 366 passed, 45 skipped (가짜 LLM·가짜 resolver/searcher로 형식·400·422·429·503·choose·칩 지우기·reset)
- `CINELOCA_TEST_DATABASE_URL=... python -m pytest -q` → 411 passed
- 실제 LLM 호출 없음. 실제 데이터로 API 전체 흐름을 돌려 보는 확인은 미실행(사전 대조·검색 템플릿의 실제 데이터 결과는 앞 PR 두 개에 있음)

## 의존성·라이선스
- [x] 새 의존성 없음
- [ ] 새 의존성 있음 → 이름·라이선스: (GPL·AGPL 계열 금지, 계획서 8.3)

## AI 활용
- [ ] 사용 안 함
- [x] 사용함 → 도구: Claude Code / 범위: 구현·테스트 작성 (계획서 부록 A에 기록)

## 체크리스트
- [x] `.env`나 API 키가 포함되지 않았다
- [x] 저장 금지 데이터(카카오 응답, 영화 이미지 파일)를 저장하지 않는다
- [x] 외부 데이터·AI 문장을 화면에 보여 준다면 출처 카드와 'AI 생성' 표시를 붙였다 (응답에 `source_ids`와 `ai_generated` 포함, 카드 조립은 남은 일)
