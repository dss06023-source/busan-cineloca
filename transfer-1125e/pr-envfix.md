## 관련 이슈
Closes #ISSUE

## 관련 요구사항·설계 ID
NFR-017, FR-615(관리자 비밀번호 해시), ADR-009(서명 키), SDD 2.4(AI 공급자 설정)

## 변경 내용
- `.env.example`: 값이 빈 17줄(`GEMINI_API_KEY`·`GEMINI_MODEL`·`GEMINI_DAILY_LIMIT`·`OLLAMA_*`·`DATA_GO_KR_SERVICE_KEY`·`KMDB_*`·`JUSO_*`·`KAKAO_REST_API_KEY`·`VITE_KAKAO_JS_KEY`·`LOG_DIR`·`ADMIN_PASSWORD_HASH`·`STAMP_SIGNING_KEY`)의 같은 줄 설명을 윗줄 주석으로 옮겼습니다. 설명 문구는 그대로이고, 값이 있는 줄(`AI_PROVIDER=gemini   # …` 등)은 건드리지 않았습니다. 맨 위에 이유를 한 줄 적었습니다.
- `backend/tests/test_env_example.py`: 값이 빈 줄에 같은 줄 설명이 있으면 실패하는 테스트입니다.
- 다른 담당 파일을 고친 이유: `.env.example`은 Docker 구성(재원 님) 파일입니다. 그런데 승근 님 PC에서 시드를 넣어 실제 데이터로 띄우다가(#137 안내 확인) AI와 관리자 기능이 꺼지는 원인으로 찾았습니다. 팀원 모두 같은 문제를 겪을 수 있어 작은 수정으로 올립니다. 리뷰어는 재원 님입니다.

### 재현과 확인
- 고치기 전: `.env.example`을 `.env`로 복사하고 `POSTGRES_PASSWORD`만 채운 뒤 `docker compose config`를 실행 → `GEMINI_DAILY_LIMIT: '# 비우면 20. …'`, `ADMIN_PASSWORD_HASH: '# 관리자 비밀번호 해시 (FR-615)'`, `STAMP_SIGNING_KEY: '# 스탬프·배지 …'`
- 고친 뒤: 같은 순서로 실행 → 세 값 모두 `""`, `AI_PROVIDER: gemini`·`SYNC_INTERVAL_DAYS: "7"`은 그대로
- 팀원 PC: 고친 `.env`로 api를 다시 만든 뒤 AI 설정 오류가 사라지고 provider=gemini로 시작함

## 테스트 방법과 결과
- `ruff check .` 통과
- `python -m pytest`: 636 passed, 76 skipped(DB 없이)
- 새 테스트가 고치기 전 파일에서는 실패하는 것 확인(`13: GEMINI_MODEL=                # 비우면 gemini-3.5-flash` 등)

## 의존성·라이선스
- [x] 새 의존성 없음
- [ ] 새 의존성 있음 → 이름·라이선스: (GPL·AGPL 계열 금지, 계획서 8.3)

## AI 활용
- [ ] 사용 안 함
- [x] 사용함 → 도구: Claude Code / 범위: 원인 찾기·수정·테스트 (계획서 부록 A에 기록)

## 체크리스트
- [x] `.env`나 API 키가 포함되지 않았다
- [x] 저장 금지 데이터(카카오 응답, 영화 이미지 파일)를 저장하지 않는다
- [x] 외부 데이터·AI 문장을 화면에 보여 준다면 출처 카드와 'AI 생성' 표시를 붙였다 (해당 없음)
