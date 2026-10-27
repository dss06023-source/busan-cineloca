`docker-entrypoint-initdb.d`로 마운트되는 폴더입니다. DB 볼륨이 비어 있을 때 한 번만 실행됩니다.

스키마는 api 컨테이너가 시작할 때 `python -m app.data.migrate`로 적용하므로 여기에 두지 않습니다.
시드(`mini_seed.sql`, `seed.sql.gz`) 적재 방법은 WP-02가 정합니다.
