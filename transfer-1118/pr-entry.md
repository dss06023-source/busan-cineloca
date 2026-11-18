#JOB_PR 위에 쌓인 PR입니다. #JOB_PR이 병합되면 main을 합쳐 이 PR의 변경만 남깁니다.

## 관련 이슈
Closes #26

## 관련 요구사항·설계 ID
FR-601~604, NFR-005, NFR-009, #39(로그 개인정보 가리기)

## 변경 내용
- `backend/app/batch/__main__.py`: 배치 실행 진입점 `python -m app.batch --once [--out 결과.json] [--env-file 파일]`
  - 리뷰 요청대로 **로그 설정 뒤 `install_privacy_log_filter()`를 붙이고, httpx·httpcore 로그 수준을 WARNING**으로 올렸습니다(httpx가 serviceKey·confmKey가 든 URL을 INFO로 남기기 때문)
  - #26: 키가 없을 때 문구가 **저장소 루트 `.env.example`**을 가리킵니다. 표준 출력·오류와 `--out` 결과 파일은 **UTF-8**로 씁니다(Windows 콘솔·파일 한글 깨짐 방지)
  - 저장소 루트 `.env`가 있으면 읽습니다(`scripts/ai_smoke.py`와 같은 방식, 이미 있는 환경변수는 덮지 않음). 빠진 선택 키(주소·카카오·KMDb)는 이름만 경고하고 그 단계만 건너뜁니다
  - 필수: `DATABASE_URL`, `DATA_GO_KR_SERVICE_KEY`. 선택: `JUSO_SEARCH_API_KEY`·`JUSO_COORD_API_KEY`, `KAKAO_REST_API_KEY`, `KMDB_SERVICE_KEY`(없으면 `KMDB_CSV_PATH`), `JUSO_BASE_URL`
- `.env.example`: `KMDB_CSV_PATH`(선택) 한 줄 추가
- 끝나면 결과 JSON(run_id, 상태, 단계별 건수, 매칭 규칙별 건수)을 출력하고, 성공이면 종료 코드 0, 가드·실패면 1, 키 없음이면 2

## 테스트 방법과 결과
- `cd backend && ruff check . && python -m pytest -q` → 340 passed, 25 skipped(DB 없이) / DB 포함 365 passed
- 새 테스트 `test_batch_main.py`: `.env` 읽기(주석·따옴표·기존 값 유지), 키 없을 때 루트 `.env.example` 안내, 빠진 선택 키는 이름만 경고(값 미노출), **로그 설정 뒤 serviceKey·confmKey 값이 출력에 없고 httpx INFO 로그가 남지 않음**
- 실제 실행: 클라우드에서 실제 원본으로 두 번 실행해 성공(건수는 #JOB_PR 본문 표)

## 의존성·라이선스
- [x] 새 의존성 없음
- [ ] 새 의존성 있음 → 이름·라이선스:

## AI 활용
- [ ] 사용 안 함
- [x] 사용함 → 도구: Claude Code / 범위: 코드·테스트 작성, 실제 실행 (계획서 부록 A에 기록)

## 체크리스트
- [x] `.env`나 API 키가 포함되지 않았다
- [x] 저장 금지 데이터(카카오 응답, 영화 이미지 파일)를 저장하지 않는다
- [ ] 외부 데이터·AI 문장을 화면에 보여 준다면 출처 카드와 'AI 생성' 표시를 붙였다 (화면 변경 없음)
