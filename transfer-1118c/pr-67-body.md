## 관련 이슈
Refs #64 (관람등급 API-003은 이 PR 위에 쌓인 #69에서 닫습니다)

## 관련 요구사항·설계 ID
FR-101~106, FR-210, FR-602, FR-604, FR-802, API-001·002, COMP-03(ArchiveService), COMP-12(WorkRepository), ADR-010

## 변경 내용
- API-001 `GET /api/works`: 작품 목록·검색(작품명·감독·배우)·장르 필터·정렬(이름·최신·촬영지 수), 한 쪽 20편. 응답 `{total, page, size, items[], sources[]}`
- API-002 `GET /api/works/{id}`: 작품 상세(줄거리·KMDb 원문 링크·출연진 최대 5명·부산 촬영지·비슷한 작품 최대 5편·출처 카드). KMDb 미매칭 작품은 작품명과 촬영지만. 없는 id는 404 `WORK_NOT_FOUND`
- 포스터·스틸은 팀 결정(11/18)에 따라 응답에서 뺐습니다. KMDb 원문 링크(`kmdb_url`)로 안내합니다(#12, BR-01)
- `app/data/works.py`(WorkRepository), `app/services/archive_service.py`(ArchiveService) 추가. 구조는 #54(MapService·LocationRepository)를 따르고 `db.connection`(503)과 출처 대장 조회를 같이 씁니다
- 이름 정규화 `norm`을 `app/core/names.py`로 옮겼습니다(동작 그대로). 배치와 조회(F1 검색, F4 사전 대조)가 같은 규칙을 쓰고 services → batch 의존이 생기지 않게 하려는 것입니다. 기존 `from app.batch.merge import norm`은 그대로 동작합니다
- 변경은 약 660줄(테스트 254줄 포함)로 기준(400줄 안팎)을 넘습니다. 목록·상세가 저장소·서비스를 같이 써서 더 나누지 않았고, 관람등급(API-003)은 #69로 뗐습니다

### SDD와 다른 점
- 응답 형식은 R3 화면(#45) 타입과 F2 관례에 맞췄습니다: 상세는 평평한 형태(`cast`, `synopsis`, `kmdb_url` …), 출처는 `source_ids` 대신 `sources`(출처 카드), 목록은 `page`·`size`·`sources` 추가와 `sort=title`(기본)
- 상세에 `poster_url`·`still_urls`가 없습니다(위 팀 결정). R3 화면(#46)의 `WorkDetailPage`가 두 칸을 읽고 있어 실제 API에 붙이면 `still_urls.length`에서 오류가 납니다. 화면 쪽에서 두 칸을 빼고 KMDb 링크로 바꿔 주세요
- 관람등급은 상세에 넣지 않습니다(API-003, #69). 화면 타입의 `rating`은 상세 응답에 없습니다
- `kind`, `locations[].scene`은 DB에 값이 없어 응답에 없습니다(R3 타입 확인 부탁드립니다)
- `genre`는 KMDb 장르 이름 그대로 받습니다(F2의 장르 묶음 12개와 다름)

### 아직 비어 있는 데이터(배치 후속 작업)
- 인물(`person`·`work_person`)·장르(`work.genres`)를 배치가 아직 채우지 않아 감독·출연·장르가 비고, 배우·감독 검색과 장르 필터는 0건입니다
- 예고편 주소는 배치가 아직 저장하지 않아 null입니다(TBD-01)

## 테스트 방법과 결과
- `cd backend && ruff format --check . && ruff check .` → 통과
- `python -m pytest -q` → 322 passed, 30 skipped (DB 없이)
- `CINELOCA_TEST_DATABASE_URL=postgresql://… python -m pytest -q` (db/init 적재한 테스트 전용 DB) → 352 passed
- 새 테스트: `test_f1_api.py`(형식·422·404), `test_archive_service_db.py`(정렬·검색·쪽 나눔·상세·비슷한 작품, 상세에 포스터·스틸 칸이 없는지)

## 의존성·라이선스
- [x] 새 의존성 없음
- [ ] 새 의존성 있음 → 이름·라이선스:

## AI 활용
- [ ] 사용 안 함
- [x] 사용함 → 도구: Claude Code / 범위: API·서비스·저장소 코드와 테스트 작성, PR 본문 초안 (계획서 부록 A에 기록)

## 체크리스트
- [x] `.env`나 API 키가 포함되지 않았다
- [x] 저장 금지 데이터(카카오 응답, 영화 이미지 파일)를 저장하지 않는다
- [x] 외부 데이터·AI 문장을 화면에 보여 준다면 출처 카드와 'AI 생성' 표시를 붙였다 — 두 응답 모두 `sources` 포함
