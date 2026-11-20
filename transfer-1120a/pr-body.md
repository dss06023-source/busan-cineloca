## 관련 이슈
Closes #65

## 관련 요구사항·설계 ID
F3 · FR-301~312 · FR-701 · FR-704 · FR-707 · API-013 · API-014 · API-015 · COMP-06 · UC-05·06

## 변경 내용
11/18에 닫은 #74를 최신 main 기준으로 다시 올립니다. #88에서 정한 대로 R2(재원님)가 리뷰합니다.
- 질문 `POST /api/query`, 후보 고르기 `POST /api/query/choose`, 조건 칩 지우기 `POST /api/query/chips/remove`, 새 대화 `DELETE /api/query/session`, 필터 패널 검색 `POST /api/search`
- #74에서 바꾼 점
  - AI를 쓰는 API-013 세 경로에 이용 안내 확인 `require_notice`를 붙였습니다(없거나 옛 버전이면 403 `NOTICE_REQUIRED`, AI를 부르지 않음). 필터 패널 검색·새 대화는 AI를 쓰지 않아 붙이지 않았습니다.
  - AI 클라이언트는 공용 `default_llm_client()`를 씁니다(F1과 호출 한도·캐시 공유). 임베딩만 따로 만들고, 설정이 틀리면 임베딩 없이 돕니다.
  - 응답에 `sources`(출처 카드: id·provider·name·base_date·url)를 넣었습니다. 각 hit의 `source_ids`가 `sources`의 id를 가리키므로 화면에서 카드를 바로 띄울 수 있습니다(FR-704, 승근 요청). 조회는 새 `services/source_cards.py`(출처 대장 `locations.sources` 사용).
  - 기능 번호를 F3·FR-301~312로 맞췄습니다(라우터 태그 "F3 AI 탐색", 테스트 파일 `test_f3_api.py`). `query_service.py` 첫 줄의 `FR-301~412` 오타도 고쳤습니다.
- 크기: 862줄 중 테스트가 412줄입니다. 질문·고르기·칩·새 대화·필터 패널이 한 라우터를 같이 써서 나누지 않았습니다.

## 테스트 방법과 결과
- `cd backend && ruff check .` → 통과
- `python -m pytest` → 588 passed, 60 skipped(DB 없음)
- `CINELOCA_TEST_DATABASE_URL=… python -m pytest`(db/init 적용 테스트 DB) → 649 passed
- 새 테스트: 이용 안내 없으면 403·AI 미호출, 필터 패널은 안내 없이 200, 출처 카드 내용·중복 ID 한 번 조회, 공용 AI 클라이언트 사용, 실제 DB에서 출처 ID → 카드 변환
- 실제 외부 API·LLM 호출 없음(가짜 공급자)

## 의존성·라이선스
- [x] 새 의존성 없음
- [ ] 새 의존성 있음 → 이름·라이선스: (GPL·AGPL 계열 금지, 계획서 8.3)

## AI 활용
- [ ] 사용 안 함
- [x] 사용함 → 도구: Claude Code / 범위: 코드·테스트 작성, PR 설명 초안

## 체크리스트
- [x] `.env`나 API 키가 포함되지 않았다
- [x] 저장 금지 데이터(카카오 응답, 영화 이미지 파일)를 저장하지 않는다
- [x] 외부 데이터·AI 문장을 화면에 보여 준다면 출처 카드와 'AI 생성' 표시를 붙였다(응답 `sources`·`ai_generated`)
