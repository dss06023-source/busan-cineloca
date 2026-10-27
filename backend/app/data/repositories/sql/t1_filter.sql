-- T1_FILTER: 기준 위치·이동 조건이 없을 때
WITH {matched}
SELECT l.id, l.name, l.gu, l.lat, l.lon,
       array_agg(DISTINCT m.work_id)   AS work_ids,
       array_agg(DISTINCT m.source_id) AS source_ids,
       NULL::real                      AS dist_m,
       NULL::real                      AS travel_min
FROM matched m
JOIN location l ON l.id = m.location_id
GROUP BY l.id
ORDER BY count(DISTINCT m.work_id) DESC, l.id
LIMIT %(limit)s
