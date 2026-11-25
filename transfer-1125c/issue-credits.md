### WBS 번호

4.2

### 관련 요구사항·설계 ID

FR-103, FR-205, FR-310, FR-303, FR-613, DATA-04

### 목적

배치가 작품의 장르(work.genres)와 감독·출연(person·work_person)을 채우지 않아, 실제 데이터에서 작품 상세의 출연진, 장르 필터, F3 배우·감독 검색, 인물 테마 추천 코스가 모두 비어 있다. 읽는 쪽(works.py, search_templates.py, dictionary.py)은 이미 있으니 KMDb 자료로 채운다.

### 작업 내용

- [ ] KMDb CSV의 장르·출연 칸 읽기, work.kmdb 저장값에 장르·감독·출연 목록 추가
- [ ] 동기화 반영 때 work.genres, person·work_person 다시 만들기(사전 재구성 앞)
- [ ] 묶음표에 없는 장르를 동기화 리포트 경고로 채우기
- [ ] 시드 갱신

### 완료 조건

시드 DB에서 KMDb에 연결된 작품에 장르·감독·출연이 들어 있고, 작품 상세·장르 필터·F3 사전(인물)이 실제 데이터로 동작한다

### 담당 역할

R4
