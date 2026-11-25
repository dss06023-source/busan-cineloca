## 관련 이슈
Closes #ISSUE

## 관련 요구사항·설계 ID
NFR-017(실행 환경), build-plan '시드 데이터'

## 변경 내용
- `db/README.md`: '시드 넣기' 절 추가
  - 순서: Release에서 받기 → SHA-256 확인(PowerShell `Get-FileHash`) → `docker compose down -v`로 빈 DB 만들기 → `docker compose cp`로 넣고 컨테이너 안에서 `gunzip | psql` → 작품 수 확인
  - Windows PowerShell에서도 그대로 되게, 압축 풀기는 컨테이너 안에서 하고 명령 안에 큰따옴표를 넣지 않았다(PowerShell 5.1이 큰따옴표를 바꿔 넘기는 문제 피함).
  - 시드에 없는 것: 추천 코스(관리자 승인 필요, `ADMIN_PASSWORD_HASH`), 검수 대기, 임베딩(#107)
- `db/README.md` init 파일 표에 `03_batch.sql`·`05_station_time.sql` 추가
- `README.md` 실행 방법에 "처음 띄우면 DB가 비어 있다, 시드 넣기는 db/README.md" 한 줄

## 테스트 방법과 결과
- 시드 적재 명령의 psql 부분(`gunzip -c seed.sql.gz | psql -q -v ON_ERROR_STOP=1 …`)을 PostgreSQL 16에서 db/init만 적용한 빈 DB에 실행: 오류 없이 끝남, 작품 436·촬영지 1,359·역 127
- `docker compose cp`·`exec` 부분은 이 환경에 Docker 엔진이 없어 미실행 → 리뷰어가 한 번 따라 해 봐 주시면 고맙겠습니다

## 의존성·라이선스
- [x] 새 의존성 없음
- [ ] 새 의존성 있음 → 이름·라이선스: (GPL·AGPL 계열 금지, 계획서 8.3)

## AI 활용
- [ ] 사용 안 함
- [x] 사용함 → 도구: Claude Code / 범위: 문서 작성 (계획서 부록 A에 기록)

## 체크리스트
- [x] `.env`나 API 키가 포함되지 않았다
- [x] 저장 금지 데이터(카카오 응답, 영화 이미지 파일)를 저장하지 않는다
- [x] 외부 데이터·AI 문장을 화면에 보여 준다면 출처 카드와 'AI 생성' 표시를 붙였다 (해당 없음)
