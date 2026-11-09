-- 출처 대장(계획서 8.1 데이터·API 대장, SRS 7.1 DATA-01~12). 저장 정책은 2026-10-27 기준.
-- '확인 필요'인 항목은 PoC·약관 확인 뒤 새 마이그레이션으로 바꾼다(머지한 파일은 고치지 않음).
INSERT INTO source(id, org, name, url, license, policy) VALUES
 ('DATA-01', '부산광역시', '부산영상위원회 영화 속 부산정보', 'https://www.data.go.kr/data/15164328/openapi.do', '이용허락범위 제한 없음', 'STORE'),
 ('DATA-02', '부산광역시', '부산영상위원회 씨네맵 정보', 'https://www.data.go.kr/data/15164338/openapi.do', '이용허락범위 제한 없음', 'STORE'),
 ('DATA-03', '부산교통공사', '영상 로케이션 촬영현황', 'https://www.humetro.busan.kr', '이용조건 확인 필요', 'STORE'),
 ('DATA-04', '한국영상자료원', 'KMDb 영화 상세 정보', 'https://www.kmdb.or.kr', '약관 원문 확인 전까지 ID만 저장(TBD-01)', 'ID_ONLY'),
 ('DATA-05', '영화진흥위원회', 'KOBIS 영화정보(통합전산망 오픈 API)', 'https://www.kobis.or.kr/kobisopenapi', '실시간 사용만, 복제·저장·재전송 금지(약관 6조)', 'ID_ONLY'),
 ('DATA-06', '행정안전부', '실시간 주소정보 조회·좌표 제공', 'https://www.data.go.kr/data/15057017/openapi.do', '이용허락범위 제한 없음', 'STORE'),
 ('DATA-07', '카카오', '카카오 지도 JS SDK·로컬 API', 'https://apis.map.kakao.com', '응답·좌표 저장과 캐시 불가', 'NO_STORE'),
 ('DATA-08', '부산교통공사', '도시철도 역사정보', 'https://www.data.go.kr/data/15158991/openapi.do', '저장 가능 여부 확인 필요', 'STORE'),
 ('DATA-09', '부산교통공사', '도시철도 운행정보(역간 소요시간)', 'https://www.humetro.busan.kr', '이용조건 확인 필요', 'STORE'),
 ('DATA-10', '한국관광공사', 'TourAPI 4.0 관광사진(부산)', 'https://api.visitkorea.or.kr', '공공누리 제1유형만 사용', 'STORE'),
 ('DATA-11', 'Google', 'Gemini API(무료 티어)', 'https://ai.google.dev', '입력이 제품 개선에 쓰일 수 있음, 마스킹 후 전송', 'NO_STORE'),
 ('DATA-12', '부산 씨네로케 팀', 'AI 평가셋', 'https://github.com/dss06023-source/busan-cineloca', '팀 저작물', 'STORE');
