CREATE TABLE source (
  id           VARCHAR(10) PRIMARY KEY,            -- DATA-01 ...
  org          TEXT NOT NULL,
  name         TEXT NOT NULL,
  url          TEXT NOT NULL,
  license      TEXT NOT NULL,
  policy       VARCHAR(8) NOT NULL CHECK (policy IN ('STORE','ID_ONLY','NO_STORE')),
  base_date    DATE,
  collected_at TIMESTAMPTZ
);

CREATE TABLE work (
  id             SERIAL PRIMARY KEY,
  ext_key        TEXT NOT NULL UNIQUE,                -- 동기화해도 id를 유지하는 자연 키(kmdb_id 또는 제목+연도)
  retired        BOOLEAN NOT NULL DEFAULT false,      -- 원본에서 사라지면 지우지 않고 숨김
  title          TEXT NOT NULL,
  title_norm     TEXT NOT NULL,
  release_year   SMALLINT,
  genres         TEXT[] NOT NULL DEFAULT '{}',
  kmdb_id        VARCHAR(20) UNIQUE,
  kobis_movie_cd VARCHAR(10),
  kmdb           JSONB,                               -- KMDb 정책이 STORE일 때만
  match_status   VARCHAR(10) NOT NULL CHECK (match_status IN ('auto','reviewed','unmatched')),
  match_score    REAL NOT NULL DEFAULT 0,
  source_id      VARCHAR(10) NOT NULL REFERENCES source(id)
);

CREATE TABLE person (
  id             SERIAL PRIMARY KEY,
  name           TEXT NOT NULL,
  kmdb_person_id VARCHAR(20) UNIQUE
);

CREATE TABLE work_person (
  work_id   INT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  person_id INT NOT NULL REFERENCES person(id) ON DELETE CASCADE,
  role      VARCHAR(8) NOT NULL CHECK (role IN ('director','actor')),
  ord       SMALLINT NOT NULL,
  PRIMARY KEY (work_id, person_id, role)
);

CREATE TABLE station (
  id   VARCHAR(10) PRIMARY KEY,
  name TEXT NOT NULL,
  line VARCHAR(10) NOT NULL,
  lat  DOUBLE PRECISION NOT NULL,
  lon  DOUBLE PRECISION NOT NULL,
  gu   VARCHAR(10) NOT NULL
);

CREATE TABLE station_time (                           -- 같은 역끼리(0분)도 넣는다
  from_id VARCHAR(10) NOT NULL REFERENCES station(id),
  to_id   VARCHAR(10) NOT NULL REFERENCES station(id),
  minutes REAL NOT NULL,
  PRIMARY KEY (from_id, to_id)
);

CREATE TABLE location (
  id                 SERIAL PRIMARY KEY,
  ext_key            TEXT NOT NULL UNIQUE,            -- 정규화 이름 + 정규화 주소(없으면 구·군)
  retired            BOOLEAN NOT NULL DEFAULT false,
  name               TEXT NOT NULL,
  name_norm          TEXT NOT NULL,
  address            TEXT,                            -- SDD는 NOT NULL, 원본에 주소 없는 레코드가 있어 허용
  gu                 VARCHAR(10),
  lat                DOUBLE PRECISION,                -- WGS84, NULL이면 지도·인증 제외
  lon                DOUBLE PRECISION,
  geocode_status     VARCHAR(8) NOT NULL CHECK (geocode_status IN ('ok','failed','manual')),
  tags               TEXT[] NOT NULL DEFAULT '{}',    -- 승인된 태그만
  caution            VARCHAR(12) NOT NULL DEFAULT 'none'
                     CHECK (caution IN ('none','private','residential','school')),
  safety_note        TEXT,
  cert_radius_m      SMALLINT NOT NULL DEFAULT 100 CHECK (cert_radius_m BETWEEN 50 AND 300),
  cert_excluded      BOOLEAN NOT NULL DEFAULT false,
  nearest_station_id VARCHAR(10) REFERENCES station(id),
  station_walk_min   SMALLINT,
  embedding          vector(1024),
  CHECK ((lat IS NULL) = (lon IS NULL))
);

CREATE TABLE shooting (
  work_id     INT NOT NULL REFERENCES work(id) ON DELETE CASCADE,
  location_id INT NOT NULL REFERENCES location(id) ON DELETE CASCADE,
  source_id   VARCHAR(10) NOT NULL REFERENCES source(id),
  raw         JSONB NOT NULL,
  base_date   DATE NOT NULL,
  PRIMARY KEY (work_id, location_id, source_id)
);

CREATE TABLE photo (
  id          SERIAL PRIMARY KEY,
  location_id INT NOT NULL REFERENCES location(id) ON DELETE CASCADE,
  url         TEXT NOT NULL,
  kogl_type   SMALLINT NOT NULL CHECK (kogl_type = 1),
  title       TEXT NOT NULL,
  source_id   VARCHAR(10) NOT NULL REFERENCES source(id)
);

CREATE TABLE course (
  id          SERIAL PRIMARY KEY,
  theme       VARCHAR(8) NOT NULL CHECK (theme IN ('work','actor','area')),
  theme_ref   TEXT,
  title       TEXT NOT NULL,
  start_label TEXT NOT NULL,
  start_lat   DOUBLE PRECISION NOT NULL,
  start_lon   DOUBLE PRECISION NOT NULL,
  total_min   INT NOT NULL,
  total_m     INT NOT NULL,
  status      VARCHAR(10) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','approved')),
  approved_by TEXT,
  approved_at TIMESTAMPTZ
);

CREATE TABLE course_stop (
  course_id   INT NOT NULL REFERENCES course(id) ON DELETE CASCADE,
  ord         SMALLINT NOT NULL,
  location_id INT NOT NULL REFERENCES location(id),
  dwell_min   SMALLINT NOT NULL DEFAULT 20,
  leg_mode    VARCHAR(6) CHECK (leg_mode IN ('walk','subway')),   -- SDD는 VARCHAR(4)
  leg_min     SMALLINT,
  leg_line    VARCHAR(10),
  PRIMARY KEY (course_id, ord)
);

CREATE TABLE review_item (
  id          BIGSERIAL PRIMARY KEY,
  kind        VARCHAR(5) NOT NULL CHECK (kind IN ('tag','match')),
  target_type VARCHAR(8) NOT NULL CHECK (target_type IN ('location','work')),
  target_id   INT NOT NULL,
  proposal    JSONB,
  proposer    VARCHAR(4) CHECK (proposer IN ('rule','ai')),
  model       TEXT,
  score       REAL,
  status      VARCHAR(8) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
  handled_by  TEXT,
  handled_at  TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE dict_entry (
  id           BIGSERIAL PRIMARY KEY,
  kind         VARCHAR(8) NOT NULL CHECK (kind IN ('work','person','gu','station','tag')),
  surface      TEXT NOT NULL,
  canonical_id TEXT NOT NULL,
  embedding    vector(1024)
);

CREATE TABLE sync_run (
  id           BIGSERIAL PRIMARY KEY,
  trigger      VARCHAR(8) NOT NULL CHECK (trigger IN ('schedule','manual')),
  status       VARCHAR(10) NOT NULL CHECK (status IN ('requested','running','published','rejected','failed')),
  requested_by TEXT NOT NULL,
  counts       JSONB,
  prev_counts  JSONB,
  failures     JSONB,
  started_at   TIMESTAMPTZ,
  finished_at  TIMESTAMPTZ
);

CREATE TABLE ai_cache (
  key        CHAR(64) PRIMARY KEY,
  task       VARCHAR(20) NOT NULL,
  response   JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE usage_counter (
  day   DATE NOT NULL,
  key   VARCHAR(40) NOT NULL,
  count INT NOT NULL DEFAULT 0,
  PRIMARY KEY (day, key)
);
