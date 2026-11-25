## 관련 이슈
Refs #112 (화면 UI-12는 다음 PR, 둘 다 병합되면 이슈를 닫습니다)

## 관련 요구사항·설계 ID
API-024 · FR-614 · FR-401·402·404 · BR-12·13 · FR-615(관리자 인증)

## 변경 내용
- `GET /api/admin/courses?status=draft|approved&theme=…`: 승인 전 포함 목록(장소 수·총 시간·거리, 계산할 수 없으면 `problem`)
- `POST /api/admin/courses` `{theme, theme_ref, max_stops(2~10, 기본 5)}` → 201 후보(승인 전)
  - 테마에 맞는 좌표 있는 촬영지 중 **작품이 가장 많이 찍힌 곳을 기준으로 가까운 곳**을 모읍니다. 인증 제외·사유지·주거지는 후보에서 뺍니다(관리자가 수정으로 넣을 수는 있음)
  - 방문 순서는 `RoutePlanner`로 정하고, 첫 장소는 모두 한 번씩 놓아 보고 이동 시간이 가장 짧은 것을 고릅니다
  - 제목 자동: 「작품」 촬영지 코스 / ○○ 출연작 촬영지 코스 / ○○구 촬영지 코스
  - 오류: 400(번호·구·군 형식) · 404 `THEME_NOT_FOUND` · 409 `NOT_ENOUGH_PLACES`(좌표 있는 곳 2곳 미만)
- `GET /api/admin/courses/{id}`: 사용자 화면(API-010)과 **같은 계산**(`CourseService.detail_of`)에 상태를 더해 돌려줌
- `PATCH /api/admin/courses/{id}` `{title?, stops?: [{location_id, stay_min}], start_station_id?, status?}`
  - 제목·장소·순서·체류·출발역을 고치면 **승인 전으로 돌아감**. `status=approved`를 함께 보내면 고친 뒤 바로 승인
  - 장소 2~10곳·중복 금지·좌표 필수, 체류 0~240분
- `DELETE /api/admin/courses/{id}`: 승인 전 후보만 삭제(승인된 것은 409 `COURSE_APPROVED`)
- 승인된 코스만 기존 API-009·010(추천 코스 목록·상세)에 나옵니다. `data/courses.py`의 조회를 상태 인자로 넓혔고 기존 동작은 같습니다
- 시드 DB로 확인: 해운대구·영도구·작품 1편 후보가 0.1초 안에 만들어짐. 다만 '촬영 스튜디오 지하기계실' 같은 곳도 들어가서 관리자 수정이 필요합니다

## 테스트 방법과 결과
- `cd backend && ruff check .` → 통과
- `python -m pytest` → 623 passed, 69 skipped(DB 없음)
- `CINELOCA_TEST_DATABASE_URL=… python -m pytest` → 692 passed
- 새 테스트: 후보 고르기(기준·가까운 곳·제외 대상), 한 번에 끝에서 끝으로 가는 순서, 오류 5종, 수정 → 승인 → 사용자 목록에 나옴 → 고치면 다시 빠짐, 잘못된 장소·역, 로그인 없으면 401

## 의존성·라이선스
- [x] 새 의존성 없음
- [ ] 새 의존성 있음 → 이름·라이선스: (GPL·AGPL 계열 금지, 계획서 8.3)

## AI 활용
- [ ] 사용 안 함
- [x] 사용함 → 도구: Claude Code / 범위: 코드·테스트 작성, PR 설명 초안

## 체크리스트
- [x] `.env`나 API 키가 포함되지 않았다
- [x] 저장 금지 데이터(카카오 응답, 영화 이미지 파일)를 저장하지 않는다
- [x] 외부 데이터·AI 문장을 화면에 보여 준다면 출처 카드와 'AI 생성' 표시를 붙였다(관리 API, 해당 없음)
