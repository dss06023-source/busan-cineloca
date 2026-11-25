### WBS 번호

4.5

### 관련 요구사항·설계 ID

FR-101~107, FR-210, FR-802, API-001~003, COMP-03(ArchiveService), COMP-12(WorkRepository), ADR-007(KMDb 단독), ADR-010

### 목적

F1 작품 아카이브 화면(UI-03·04, #45)이 목업 대신 실제 DB를 읽게 작품 목록·상세·관람등급 API를 만든다.

### 작업 내용

- [ ] API-001 `GET /api/works` 목록·검색(작품명·감독·배우)·장르 필터·정렬, 한 쪽 20편
- [ ] API-002 `GET /api/works/{id}` 상세(줄거리·KMDb 링크·출연진·부산 촬영지·비슷한 작품·출처 카드). 포스터·스틸은 주지 않음(구현 기준 정정표 11/18)
- [ ] API-003 `GET /api/works/{id}/rating` 관람등급: 배치가 저장한 KMDb 값(ADR-007, KOBIS 제외)
- [ ] 이름 정규화 `norm`을 `app/core/names.py`로 옮겨 배치·조회가 같이 쓰기

### 완료 조건

- [ ] 단위 테스트 통과(CI), DB 테스트 통과(테스트 전용 DB)
- [ ] 등급이 없으면 상세 화면이 막히지 않음(rating null → '정보 없음')

### 담당 역할

R4 이승근 (데이터·SQL·테스트)
