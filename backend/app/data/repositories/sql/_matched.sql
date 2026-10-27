matched AS (                       -- 작품·인물·장르·구·군·연도 조건을 통과한 (촬영지, 작품) 쌍
  SELECT s.location_id, s.work_id, s.source_id
  FROM shooting s
  JOIN work w     ON w.id = s.work_id
  JOIN location l ON l.id = s.location_id
  WHERE NOT l.retired AND NOT w.retired
    AND (%(work_ids)s::int[]   IS NULL OR w.id = ANY(%(work_ids)s::int[]))
    AND (%(person_ids)s::int[] IS NULL OR EXISTS (
          SELECT 1 FROM work_person wp
          WHERE wp.work_id = w.id AND wp.person_id = ANY(%(person_ids)s::int[])))
    AND (%(genres)s::text[]    IS NULL OR w.genres && %(genres)s::text[])
    AND (%(gus)s::text[]       IS NULL OR l.gu = ANY(%(gus)s::text[]))
    AND (%(year_from)s::int    IS NULL OR w.release_year >= %(year_from)s::int)
    AND (%(year_to)s::int      IS NULL OR w.release_year <= %(year_to)s::int)
)
