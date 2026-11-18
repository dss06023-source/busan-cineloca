C1 배치(실제 원본)로 만든 전체 시드입니다. 저장소에는 넣지 않고 Release로만 배포합니다(build-plan '시드 데이터').

**미리 보기(pre-release)**: 배치 코드 #57(좌표)·#JOB_PR(배치 실행)·#ENTRY_PR(진입점)이 아직 병합 전입니다. 병합 뒤 같은 코드로 다시 만들어 정식 Release로 바꿉니다.

### 들어 있는 것 (2026-11-18 실행, 같은 원본으로 세 번 돌려 id 같음 확인)
- 작품 436편, 촬영지 1,359곳(좌표 933곳, 모두 주소 API), 촬영 기록 4,255건, 도시철도역 127곳(최근접 역 933곳)
- 주소가 없거나 동까지만 있는 426곳은 위치 미확인(FR-210). #57 팀장 결정대로 카카오 키워드 좌표는 넣지 않았습니다(`GEOCODE_KAKAO_KEYWORD=false`)
- KMDb 매칭(KMDb '영화기본정보' CSV 기준): 자동 355 · 검수 대기 53 · 미매칭 28. 검수 대기 53건은 review_item에 들어 있음
- 비어 있는 것: 인물·장르·사전(dict_entry)·코스·임베딩(배치 후속 작업)

### 넣지 않은 것
- API 키·비밀값 없음(키 값으로 전체 검사), sync_run·ai_cache·usage_counter·stg 데이터 없음
- 저장 금지 데이터 없음: 카카오 응답·카카오 좌표, KOBIS 응답, 영화 이미지 파일
- source 표는 db/init이 넣으므로 시드에서 뺌

### 적재 방법(데이터만 들어 있음, 스키마는 db/init이 만듦)
1. 새 DB로 시작: `docker compose down -v` → `docker compose up -d db` (db/init 01~03이 스키마를 만듦)
2. `gunzip -c seed.sql.gz | docker compose exec -T db psql -U cineloca -d cineloca -v ON_ERROR_STOP=1`
   (Windows PowerShell은 Git Bash에서 실행하거나 `docker compose cp`로 넣은 뒤 컨테이너 안에서 `gunzip -c … | psql`)
3. 확인: `SELECT count(*) FROM work;` → 436
- 파일 무결성: `seed.sha256.txt`의 SHA-256과 비교

### 출처·이용조건
- 부산영상위원회 영화 속 부산정보(DATA-01)·씨네맵(DATA-02), 부산교통공사 역사 정보(DATA-08): 공공데이터포털
- 촬영지 좌표: 행정안전부 도로명주소 API(DATA-06)
- 줄거리·키워드: 한국영상자료원 KMDb, 공공누리 제1유형(출처 표시, #12)
