-- 동기화 스테이징(ADR-012, build-plan 7장 '동기화 반영 규칙').
-- 배치는 여기에 적재하고 건수 가드를 통과하면 한 트랜잭션으로 public에 반영한다.
-- 관계는 id가 아니라 ext_key로 잇는다. public의 id는 반영할 때 ext_key로 맞춘다.
CREATE SCHEMA stg;

CREATE TABLE stg.work (
  ext_key        TEXT PRIMARY KEY,
  title          TEXT NOT NULL,
  title_norm     TEXT NOT NULL,
  release_year   SMALLINT,
  genres         TEXT[] NOT NULL DEFAULT '{}',
  kmdb_id        VARCHAR(20),
  kobis_movie_cd VARCHAR(10),
  match_status   VARCHAR(10) NOT NULL CHECK (match_status IN ('auto','reviewed','unmatched')),
  match_score    REAL NOT NULL DEFAULT 0,
  source_id      VARCHAR(10) NOT NULL
);

CREATE TABLE stg.location (
  ext_key            TEXT PRIMARY KEY,
  name               TEXT NOT NULL,
  name_norm          TEXT NOT NULL,
  address            TEXT,
  gu                 VARCHAR(10),
  lat                DOUBLE PRECISION,
  lon                DOUBLE PRECISION,
  geocode_status     VARCHAR(8) NOT NULL CHECK (geocode_status IN ('ok','failed')),
  nearest_station_id VARCHAR(10),
  station_walk_min   SMALLINT,
  CHECK ((lat IS NULL) = (lon IS NULL))
);

CREATE TABLE stg.shooting (
  work_key     TEXT NOT NULL REFERENCES stg.work(ext_key),
  location_key TEXT NOT NULL REFERENCES stg.location(ext_key),
  source_id    VARCHAR(10) NOT NULL,
  raw          JSONB NOT NULL,
  base_date    DATE NOT NULL,
  PRIMARY KEY (work_key, location_key, source_id)
);
