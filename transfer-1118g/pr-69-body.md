#67이 병합돼(044502d) main을 합치고 base를 main으로 바꿨습니다.

## 관련 이슈
Closes #64

## 관련 요구사항·설계 ID
FR-107, API-003, ADR-007(영화 정보는 KMDb 단독, KOBIS 제외), COMP-03(ArchiveService.get_rating), 구현 기준 정정표(11/18)

## 변경 내용
리뷰 수정 요청(11/9 수정본 ADR-007·FR-107)대로 KOBIS를 빼고, 배치가 저장한 KMDb 관람등급을 돌려주게 바꿨습니다.
- API-003 `GET /api/works/{id}/rating`: `work.kmdb`에 저장된 KMDb 관람등급을 돌려줍니다. 응답 `{rating: 문자열 또는 null, sources[]}`
  - 등급이 있으면 출처 카드 KMDb(DATA-04), 없으면 `rating: null`(화면은 '정보 없음')
  - 없는 작품은 404 `WORK_NOT_FOUND`
  - KMDb는 STORE(#12·#58)라 실시간 조회는 하지 않습니다
  - 경로는 SDD대로 따로 둡니다(화면 #45와 맞추기 쉽게)
- 배치 `stored_kmdb()`: KMDb 관람등급을 `work.kmdb.rating`에 함께 저장합니다. CSV(영화기본정보)는 18번 칸 '대표영화관람등급'을 읽습니다
- 뺀 것: `app/data/kobis.py`, `tests/test_kobis.py`, `KOBIS_API_KEY`(.env.example·config.py), `db/init/04_f1_works.sql`(`work.kobis_movie_cd` 열, KOBIS 출처 DATA-05)
  - 이제 기존 DB에 따로 적용할 파일이 없습니다
  - DATA-05는 팀 출처 대장에서 TourAPI 번호라, 겹치던 번호도 없어졌습니다
- 주석 정리: 상세의 포스터·예고편 주석을 정정표에 맞춤(포스터·스틸은 저장·표시 안 함, TBD-01 닫힘)
- 화면(#45)은 상세의 `rating`을 읽고 있어 `/works/{id}/rating`을 따로 부르도록 바꿔야 합니다(R3 확인 부탁드립니다)

### 확인 필요: 지금은 등급 데이터가 없습니다
- 배치가 쓰는 KMDb CSV('영화기본정보', 2026-11-13, 10만 행)는 '대표영화관람등급' 칸이 **10만 행 모두 비어 있습니다**('null'). 부산행·해운대·국제시장도 비어 있습니다. 그래서 이 PR을 반영해도 당분간 모든 작품이 '정보 없음'입니다
- KMDb 오픈API 응답의 등급 필드는 키가 없어 실제 응답으로 확인하지 못했습니다. AGENTS.md(응답 필드를 추측하지 않음)에 따라, 키를 받으면 응답 사본을 `tests/fixtures/real/`에 넣고 API 경로의 등급 읽기를 더하겠습니다

## 테스트 방법과 결과
- `cd backend && ruff format --check . && ruff check .` → 통과
- main(014362d) 합친 뒤: DB 없이 428 passed, 35 skipped / 테스트 DB 463 passed
- main에 #71·#72·#73·#78·#84와 이 PR을 모두 합친 상태(db/init 01~03 + 05) → 533 passed
- 바뀐 테스트
  - `test_f1_api.py`: 등급 있음 → DATA-04 카드, 없음·빈 문자열 → null, 없는 작품 → 404
  - `test_archive_service_db.py`: 저장값 읽기, KMDb 미연결 작품, 저장본 없는 작품
  - `test_batch_kmdb.py`: `stored_kmdb()`에 rating, CSV 18번 칸

## 의존성·라이선스
- [x] 새 의존성 없음
- [ ] 새 의존성 있음 → 이름·라이선스:

## AI 활용
- [ ] 사용 안 함
- [x] 사용함 → 도구: Claude Code / 범위: 리뷰 반영 코드·테스트 수정, CSV 칸 확인, PR 본문 초안 (계획서 부록 A에 기록)

## 체크리스트
- [x] `.env`나 API 키가 포함되지 않았다
- [x] 저장 금지 데이터(카카오 응답, 영화 이미지 파일)를 저장하지 않는다 — KOBIS 호출을 뺐고, KMDb 등급은 텍스트(공공누리 제1유형, #58)
- [x] 외부 데이터·AI 문장을 화면에 보여 준다면 출처 카드와 'AI 생성' 표시를 붙였다 — 등급이 있으면 `sources`에 DATA-04 카드
