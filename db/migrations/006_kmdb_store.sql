-- TBD-01 결정(2026-10-27, 팀): KMDb(DATA-04)는 줄거리·키워드·링크를 work.kmdb에 저장한다(ID_ONLY → STORE).
-- 키 승인 전에는 오픈자료 '영화기본정보' CSV(KmdbCsvCatalog)에서 채운다. 포스터·스틸 이미지 파일은 계속 저장하지 않는다.
UPDATE source
   SET policy = 'STORE',
       license = '팀 결정으로 줄거리·키워드·링크 저장(TBD-01, 2026-10-27). 이미지 파일은 저장 안 함'
 WHERE id = 'DATA-04';

-- 배치가 매칭한 KMDb 저장본을 반영 단계까지 실어 나른다(work.kmdb와 같은 모양)
ALTER TABLE stg.work ADD COLUMN kmdb JSONB;
