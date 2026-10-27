-- 테스트 전용 가짜 데이터: 작품-촬영지 연결과 좌표·소요시간은 실제 정보가 아니다. 템플릿 SQL 확인용.
INSERT INTO source(id, org, name, url, license, policy) VALUES
 ('DATA-01','부산광역시','영화 속 부산정보','https://www.data.go.kr/data/15164328/openapi.do','이용허락범위 제한 없음','STORE'),
 ('DATA-02','부산광역시','씨네맵 정보','https://www.data.go.kr/data/15164338/openapi.do','이용허락범위 제한 없음','STORE'),
 ('DATA-04','한국영상자료원','KMDb','https://www.kmdb.or.kr','약관 확인','ID_ONLY')
ON CONFLICT (id) DO NOTHING;  -- 004_sources가 이미 넣은 행은 그대로 둔다
INSERT INTO station(id,name,line,lat,lon,gu) VALUES
 ('119','서면','1호선',35.1579,129.0594,'부산진구'),
 ('113','부산역','1호선',35.1152,129.0422,'동구'),
 ('203','해운대','2호선',35.1634,129.1586,'해운대구'),
 ('209','광안','2호선',35.1576,129.1131,'수영구');
INSERT INTO station_time VALUES
 ('119','119',0),('113','113',0),('203','203',0),('209','209',0),
 ('119','113',12),('113','119',12),('119','203',28),('203','119',28),
 ('119','209',18),('209','119',18),('209','203',10),('203','209',10),('113','203',40),('203','113',40),('113','209',30),('209','113',30);
INSERT INTO location(ext_key,name,name_norm,address,gu,lat,lon,geocode_status,nearest_station_id,station_walk_min,tags) VALUES
 ('L1','해운대해수욕장','해운대해수욕장','부산 해운대구 우동','해운대구',35.1587,129.1604,'ok','203',9,'{바다}'),
 ('L2','광안리해수욕장','광안리해수욕장','부산 수영구 광안동','수영구',35.1532,129.1186,'ok','209',11,'{바다,야경}'),
 ('L3','서면 젊음의거리','서면젊음의거리','부산 부산진구 부전동','부산진구',35.1557,129.0598,'ok','119',4,'{번화가}'),
 ('L4','영도대교','영도대교','부산 영도구 대교동','영도구',35.0950,129.0368,'ok','113',31,'{다리}'),
 ('L5','주소 없는 장소','주소없는장소',NULL,NULL,NULL,NULL,'failed',NULL,NULL,'{}');
INSERT INTO work(ext_key,title,title_norm,release_year,genres,match_status,source_id) VALUES
 ('W1','범죄도시','범죄도시',2017,'{범죄,액션}','auto','DATA-01'),
 ('W2','부산행','부산행',2016,'{액션,스릴러}','auto','DATA-01'),
 ('W3','해운대','해운대',2009,'{드라마,재난}','auto','DATA-02'),
 ('W4','친구','친구',2001,'{드라마}','reviewed','DATA-02');
INSERT INTO person(name) VALUES ('마동석'),('윤제균');
INSERT INTO work_person VALUES (1,1,'actor',1),(2,1,'actor',2),(3,2,'director',1);
INSERT INTO shooting(work_id,location_id,source_id,raw,base_date) VALUES
 (1,3,'DATA-01','{}','2026-09-30'),(1,2,'DATA-01','{}','2026-09-30'),
 (2,4,'DATA-01','{}','2026-09-30'),(3,1,'DATA-02','{}','2026-09-30'),
 (3,2,'DATA-02','{}','2026-09-30'),(4,4,'DATA-02','{}','2026-09-30'),(4,5,'DATA-02','{}','2026-09-30');

UPDATE location SET retired = true WHERE ext_key = 'L4';
