-- T3_NEAR_STATION: base_station이 없으면 '아무 역에서 걸어서 N분',
--                  있으면 '그 역에서 도시철도 + 내려서 걷기 N분'
WITH {matched}
SELECT l.id, l.name, l.gu, l.lat, l.lon,
       array_agg(DISTINCT m.work_id)   AS work_ids,
       array_agg(DISTINCT m.source_id) AS source_ids,
       NULL::real AS dist_m,
       (COALESCE(st.minutes, 0) + l.station_walk_min)::real AS travel_min
FROM matched m
JOIN location l ON l.id = m.location_id
LEFT JOIN station_time st
       ON st.from_id = %(base_station)s::text AND st.to_id = l.nearest_station_id
WHERE l.nearest_station_id IS NOT NULL
  AND (%(base_station)s::text IS NULL OR st.minutes IS NOT NULL)
  AND COALESCE(st.minutes, 0) + l.station_walk_min <= %(minutes)s
GROUP BY l.id, st.minutes
ORDER BY travel_min, l.id
LIMIT %(limit)s
