C1 배치(실제 원본)로 만든 전체 시드입니다. 저장소에는 넣지 않고 Release로만 배포합니다(build-plan '시드 데이터').

**미리 보기(pre-release)**: seed-2026-11-18b에 작품 장르·감독·출연과 F3 사전을 더한 판입니다. 작품·촬영지·좌표·id는 11/18b와 같습니다. 장르·출연을 채우는 배치 코드 PR(#CREDITS)이 병합되면 정식 Release로 바꿉니다.

### 11/18b에서 바뀐 것
- 장르: KMDb에 연결된 355편 모두(work.genres). 묶음표에 없는 장르 0종
- 감독·출연: 사람 2,023명, 작품 연결 3,846건(출연은 작품마다 앞 10명)
- F3 사전(dict_entry) 2,828개: 작품 524, 인물 2,023, 역 254, 구·군 27
- 만드는 방법: 11/18b를 현재 main 스키마에 넣고, #CREDITS의 코드로 같은 KMDb CSV에서 장르·감독·출연을 다시 읽은 뒤 반영 단계(credits.apply → dictionary.rebuild)를 돌림. 공공데이터 원본은 다시 받지 않음(11/25 클라우드에서 data.go.kr·주소 API 연결 불가). 줄거리·키워드·링크·등급은 355편 모두 11/18b와 같음

### 들어 있는 것
- 작품 436편, 촬영지 1,359곳(좌표 933곳, 모두 주소 API), 촬영 기록 4,255건, 도시철도역 127곳
- 역간 소요시간 16,002줄(DATA-09)
- 주소가 없거나 동까지만 있는 426곳은 위치 미확인(FR-210). 카카오 키워드 좌표는 넣지 않음(GEOCODE_KAKAO_KEYWORD=false)
- KMDb 매칭(영화기본정보 CSV 기준): 자동 355 · 검수 대기 53 · 미매칭 28. 검수 대기 53건은 review_item에 들어 있음
- 비어 있는 것: 추천 코스(관리자 승인 필요), 임베딩(#107), 사진

### 넣지 않은 것
- API 키·비밀값 없음(키 값으로 전체 검사), sync_run·ai_cache·usage_counter·stg 데이터 없음
- 저장 금지 데이터 없음: 카카오 응답·카카오 좌표, KOBIS 응답, 영화 이미지 파일
- source 표는 db/init이 넣으므로 시드에서 뺌

### 적재 방법
db/README.md '시드 넣기'(#SEEDDOC)를 따릅니다. 요약:
1. 빈 DB: `docker compose down -v` → `docker compose up -d db`
2. `docker compose cp seed.sql.gz db:/tmp/seed.sql.gz`
3. `docker compose exec db sh -c 'gunzip -c /tmp/seed.sql.gz | psql -q -v ON_ERROR_STOP=1 -U $POSTGRES_USER -d $POSTGRES_DB'`
4. 확인: `SELECT count(*) FROM work;` → 436
- 파일 무결성 SHA-256: `569b569001024916b447d1d5d0c21a9a1931d5dff00a3f83284a4502981b355f`

### 출처·이용조건
- 부산영상위원회 영화 속 부산정보(DATA-01)·씨네맵(DATA-02), 부산교통공사 역사 정보(DATA-08)·역간 거리 및 소요시간 정보(DATA-09): 공공데이터포털
- 촬영지 좌표: 행정안전부 도로명주소 API(DATA-06)
- 줄거리·키워드·장르·감독·출연: 한국영상자료원 KMDb, 공공누리 제1유형(출처 표시, #12)
