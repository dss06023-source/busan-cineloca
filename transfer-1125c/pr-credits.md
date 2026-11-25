## 관련 이슈
Closes #ISSUE

## 관련 요구사항·설계 ID
FR-103(출연 표시), FR-205·FR-310(장르 필터), FR-303(F3 사전: 인물), FR-613(동기화 리포트 경고), DATA-04(KMDb, 공공누리 제1유형)

## 변경 내용
- `app/batch/kmdb.py`: KMDb CSV의 장르(7번 칸)·출연(12번 칸)을 읽는다. `stored_kmdb()`가 `genres`·`directors`·`actors` 목록을 더한다.
  - 출연은 앞 10명만 둔다(`ACTOR_LIMIT`). 단역 수백 명이 F3 배우 검색에 섞이지 않게 하려는 것이다. 화면은 5명을 보여 준다.
  - 출연 칸은 `이름(배역),이름(배역)` 꼴이라 괄호를 떼고 이름만 쓴다(`names()`). 장르의 괄호(`사회물(경향)`)는 묶음표 이름의 일부라 그대로 둔다(`genre_list()`).
  - 오픈API 응답의 장르·출연 필드는 실제 응답 사본이 없어 읽지 않는다(AGENTS.md). 감독은 기존대로 읽는다.
- `app/data/credits.py`(새 파일): 반영 단계에서 `work.kmdb` 저장값을 `work.genres`와 `person`·`work_person`으로 옮긴다.
  - 사람은 이름으로 찾고, 없으면 새로 만든다. KMDb CSV에는 인물 번호가 없어서 이름이 같으면 같은 사람으로 본다(`kmdb_person_id`는 비워 둠). SDD와 다른 점이다.
  - 사람 행은 지우지 않는다. 인물 테마 추천 코스가 `person.id`를 가리킬 수 있기 때문이다.
  - KMDb 연결이 끊기거나 저장값이 없는 작품은 장르와 출연을 비운다.
- `app/data/staging.py`: `publish()`가 사전 재구성(`dictionary.rebuild`) 앞에서 `credits.apply()`를 부른다. 그래서 F3 사전에 인물이 바로 들어간다.
- `app/batch/job.py`: 묶음표에 없는 KMDb 장르를 `counts.unknown_genres`에 채운다(동기화 리포트 경고, FR-613). 이 칸은 있었지만 지금까지 채우는 곳이 없었다.
- 기대값 변경: `test_stored_kmdb_has_no_image_fields`의 저장값에 `genres`·`directors`·`actors` 키가 늘었다(빈 목록). 이미지 필드가 없다는 검사는 그대로다.

### 11/18 시드에 적용한 결과(같은 KMDb CSV, 원본 재수집 없이)
- KMDb에 연결된 355편 모두 장르가 들어갔고, 사람 2,023명·연결 3,846건이 생겼다. 사전의 person 항목은 0개에서 2,023개가 됐다.
- 묶음표에 없는 장르는 0종이다(처음 구현에서 장르 괄호를 떼어 `사회물`·`하이틴` 2종이 경고로 나와서 고쳤다).
- 표본 확인: 부산행은 액션·스릴러·재난, 감독 연상호, 출연 공유·정유미·마동석… / 해운대는 감독 윤제균, 출연 설경구·하지원…
- 줄거리·키워드·링크·등급은 바뀌지 않았다(355편 모두 이전 값과 같음).
- 이 결과로 만든 시드를 Release `seed-2026-11-25`(미리 보기)로 올렸다. 이 PR이 병합되면 정식으로 바꾼다.

## 테스트 방법과 결과
- `ruff check .` 통과
- `CINELOCA_TEST_DATABASE_URL=… python -m pytest`: 688 passed(DB 포함). DB 없이: 621 passed, 67 skipped
- 새 테스트: `test_stored_kmdb_keeps_genres_directors_and_first_actors`, `test_names_drops_roles_keeps_order_and_skips_repeats`, CSV 장르·출연 칸 읽기, `test_unknown_genres_lists_kmdb_genres_outside_groups`, `tests/test_credits_db.py`(장르·사람 반영, 두 번 돌려도 사람 id 유지, 사전에 인물 반영)
- 실제 API 확인(시드 DB): `GET /api/works/{부산행}` → genres·director·cast가 채워짐, `GET /api/works?genre=재난` → 7편

## 의존성·라이선스
- [x] 새 의존성 없음
- [ ] 새 의존성 있음 → 이름·라이선스: (GPL·AGPL 계열 금지, 계획서 8.3)

## AI 활용
- [ ] 사용 안 함
- [x] 사용함 → 도구: Claude Code / 범위: 구현·테스트·시드 검증 (계획서 부록 A에 기록)

## 체크리스트
- [x] `.env`나 API 키가 포함되지 않았다
- [x] 저장 금지 데이터(카카오 응답, 영화 이미지 파일)를 저장하지 않는다
- [x] 외부 데이터·AI 문장을 화면에 보여 준다면 출처 카드와 'AI 생성' 표시를 붙였다 (화면 변경 없음. 장르·출연은 KMDb 출처로 기존 작품 출처 표시를 따름)
