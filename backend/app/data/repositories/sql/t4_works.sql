-- T4_WORKS: 결과 유형이 작품일 때
WITH {matched}
SELECT w.id, w.title, w.release_year, w.genres,
       count(DISTINCT m.location_id)   AS location_count,
       array_agg(DISTINCT m.source_id) AS source_ids
FROM matched m
JOIN work w ON w.id = m.work_id
GROUP BY w.id
ORDER BY location_count DESC, w.release_year DESC NULLS LAST, w.id
LIMIT %(limit)s
