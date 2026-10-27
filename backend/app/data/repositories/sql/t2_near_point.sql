-- T2_NEAR_POINT: 기준점(현재 위치·장소·특정 역)에서 반경 안. 도보 N분이면 radius_m = N × 4000/60 ÷ 1.3
WITH {matched}
SELECT l.id, l.name, l.gu, l.lat, l.lon,
       array_agg(DISTINCT m.work_id)   AS work_ids,
       array_agg(DISTINCT m.source_id) AS source_ids,
       earth_distance(ll_to_earth(%(lat)s, %(lon)s), ll_to_earth(l.lat, l.lon))::real AS dist_m,
       NULL::real AS travel_min
FROM matched m
JOIN location l ON l.id = m.location_id
WHERE l.lat IS NOT NULL
  AND earth_box(ll_to_earth(%(lat)s, %(lon)s), %(radius_m)s) @> ll_to_earth(l.lat, l.lon)
  AND earth_distance(ll_to_earth(%(lat)s, %(lon)s), ll_to_earth(l.lat, l.lon)) <= %(radius_m)s
GROUP BY l.id
ORDER BY dist_m, l.id
LIMIT %(limit)s
