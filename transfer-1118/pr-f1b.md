#F1A_PR 위에 쌓인 PR입니다. #F1A_PR이 병합되면 main을 합쳐 이 PR의 변경만 남깁니다.

## 관련 이슈
Closes #F1_ISSUE

## 관련 요구사항·설계 ID
FR-107, API-003, COMP-03(ArchiveService.get_rating), COMP-11(RatingProvider), ADR-007, ERR-006

## 변경 내용
- API-003 `GET /api/works/{id}/rating`: KOBIS 관람등급 실시간 조회(3초 제한). 응답 `{rating: 문자열 또는 null, sources[]}`
- 영화 코드 없음·`KOBIS_API_KEY` 없음·실패·시간 초과는 모두 200에 `rating: null`(상세 화면을 막지 않음). 없는 작품은 404 `WORK_NOT_FOUND`
- `app/data/kobis.py`: KOBIS 클라이언트. 응답에서 등급 문자열만 꺼내고 본문은 DB·캐시·파일·로그·픽스처 어디에도 남기지 않습니다. 로그에는 공급자·오류 종류·걸린 시간만 남깁니다
- `db/init/04_f1_works.sql`: `work.kobis_movie_cd` 열(SDD 3.5)과 KOBIS 출처(DATA-05, ID_ONLY) 추가 → **기존 개발·테스트 DB에 이 파일을 한 번 적용해야 합니다** (`psql -f db/init/04_f1_works.sql`)
- `.env.example`에 `KOBIS_API_KEY` 이름 추가(비우면 등급은 늘 null)

### SDD와 다른 점
- 출처는 `source_ids` 대신 `sources`(출처 카드)로 줍니다(F2·API-001·002와 같음)
- 화면(#45)은 상세의 `rating`을 읽고 있어 `/works/{id}/rating`을 따로 부르도록 바꿔야 합니다(R3 확인 부탁드립니다)
- KOBIS 출처 번호 DATA-05는 착수 PoC 보고서의 번호를 따랐습니다. 팀 출처 대장 번호와 다르면 알려 주세요

### 아직 비어 있는 데이터(배치 후속 작업)
- `kobis_movie_cd`를 채우는 배치가 없어 지금은 실제 등급이 항상 null입니다
- KOBIS 호출 수 집계(`usage_counter`, NFR-018)는 넣지 않았습니다

## 테스트 방법과 결과
- `cd backend && ruff format --check . && ruff check .` → 통과
- `python -m pytest -q` → 338 passed, 31 skipped (DB 없이, main 429752f + #F1A_PR에 적용해 확인)
- `CINELOCA_TEST_DATABASE_URL=postgresql://… python -m pytest -q` (db/init 01~04 적재한 테스트 전용 DB) → 통과
- 새 테스트: `test_kobis.py`(등급 추출·실패·시간 초과·키 미노출), `test_f1_api.py`(등급 null 200·404·실패와 시간 초과 강등·코드 없으면 KOBIS 미호출), `test_archive_service_db.py`(코드만 읽어 등급 조회)
- KOBIS 테스트는 `httpx.MockTransport`와 손으로 만든 가짜 응답만 씁니다(실제 호출·응답 사본 없음)

## 의존성·라이선스
- [x] 새 의존성 없음
- [ ] 새 의존성 있음 → 이름·라이선스:

## AI 활용
- [ ] 사용 안 함
- [x] 사용함 → 도구: Claude Code / 범위: KOBIS 클라이언트·서비스·라우터 코드와 테스트 작성, PR 본문 초안 (계획서 부록 A에 기록)

## 체크리스트
- [x] `.env`나 API 키가 포함되지 않았다
- [x] 저장 금지 데이터(카카오 응답, 영화 이미지 파일)를 저장하지 않는다 — KOBIS 응답 본문도 저장·로그·픽스처에 없음
- [x] 외부 데이터·AI 문장을 화면에 보여 준다면 출처 카드와 'AI 생성' 표시를 붙였다 — 등급이 있으면 `sources`에 DATA-05 카드
