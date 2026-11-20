#67이 병합돼(044502d) main을 합쳤습니다. 기능 내용은 승인받은 그대로이고, 주석의 기능 번호만 구현 기준 정정표(11/18)에 맞췄습니다(F4 → F3, FR-403 → FR-303). base를 바꾸면서 승인이 풀려 다시 리뷰를 부탁드립니다.

## 관련 이슈
Refs #65

## 관련 요구사항·설계 ID
FR-303, FR-617(질의 벡터를 받는 조회만), COMP-06·12, ADR-008·010·012, UC-05 4·4a·4b

## 변경 내용
- `app/data/dictionary.py`: `rebuild()`로 dict_entry를 지식베이스에서 다시 맞춤(작품 제목과 방송사·OTT 머리말 뗀 제목, 인물, 역 이름과 'X역', 구·군 16개와 짧은 이름 11개). 표기는 `app.core.names.norm`으로 정규화. 바뀌지 않은 행은 두어 embedding 유지
- `lookup()`: 정확 일치 → 트라이그램 0.35 이상 상위 3개 → (질의 벡터를 받았을 때만) 코사인 0.75. `lookup_place()`: 좌표 있는 촬영지 이름
- `staging.publish()` 끝에서 같은 트랜잭션으로 `rebuild()` 호출
- `app/services/entity_resolver.py`: `DictionaryResolver`(EntityResolver 구현). 후보가 여럿(같은 이름 또는 1등과 0.05 안)이면 Choice, 사전에 없으면 unknown, 역 이름이 없으면 '아무 역'
- 머리말 규칙(`split_media`)과 역 표시 이름(`station_label`)을 `app/core/names.py`에 두고 `app/batch/kmdb.py`는 import만 바꿈(data 계층이 batch를 import하지 않게)
- SDD·build-plan과 다른 점: ① NFKC 없이 기존 `norm()` 사용 ② 기준 장소는 similarity와 word_similarity 중 큰 값(줄여 부른 이름 대응) ③ 기준 위치를 못 찾으면 이동 조건도 뺌
- 400줄을 넘음(880줄, 절반이 테스트)

### 이번에 바뀐 것
- main 합치기: #67 squash와 이 브랜치의 `app/core/names.py`가 같은 파일을 새로 만든 것으로 보여 충돌했습니다. main의 names.py가 #67 마지막 커밋과 같아 이 브랜치 쪽(머리말 규칙 추가본)을 썼습니다. 결과는 'main + 이 PR의 원래 변경'과 같습니다(tree 비교)
- 주석 번호: F4 사전 → F3 사전, FR-403 → FR-303, names.py의 'F4 EntityResolver' → 'F3 EntityResolver'

## 테스트 방법과 결과
- `ruff format --check .`, `ruff check .` 통과
- main(014362d) 합친 뒤: `python -m pytest -q` → 433 passed, 43 skipped / `CINELOCA_TEST_DATABASE_URL=... python -m pytest -q` → 476 passed
- 배치 결과 DB 사본(작품 436, 촬영지 1,359, 역 127)에서 `rebuild()` 실행: dict_entry 805행(work 524, station 254, district 27)
  - 역 '부산역' → 정확 일치 1건, 역 '서면' → 1·2호선 2건이라 Choice('서면역 (1호선)' / '서면역 (2호선)')
  - 작품 '나의 해방일지' → 머리말 뗀 제목으로 정확 일치
  - 장소 '광안리' → 광안리해수욕장(0.75, 2등 0.5), 장소 '해운대' → 0.75 동점 3곳이라 Choice
- 인물 문항은 인물 데이터(person·work_person)가 아직 없어 확인 못 함(DB 테스트의 가짜 데이터로만 확인)

## 의존성·라이선스
- [x] 새 의존성 없음
- [ ] 새 의존성 있음 → 이름·라이선스: (GPL·AGPL 계열 금지, 계획서 8.3)

## AI 활용
- [ ] 사용 안 함
- [x] 사용함 → 도구: Claude Code / 범위: 구현·테스트 작성, main 합치기 충돌 해결 (계획서 부록 A에 기록)

## 체크리스트
- [x] `.env`나 API 키가 포함되지 않았다
- [x] 저장 금지 데이터(카카오 응답, 영화 이미지 파일)를 저장하지 않는다
- [x] 외부 데이터·AI 문장을 화면에 보여 준다면 출처 카드와 'AI 생성' 표시를 붙였다 (화면 없음)
