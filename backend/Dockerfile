# 빌드 맥락: 저장소 루트(docker-compose.yml의 api·batch). 저장소와 같은 배치로 복사해
# 코드가 db/migrations·config·backend/prompts를 저장소 루트 기준 상대 경로로 찾는다.
FROM python:3.12-slim
WORKDIR /srv/backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/pyproject.toml ./
COPY backend/app ./app
# 편집 가능 설치: 코드가 /srv/backend에 남아 상대 경로가 유지된다
RUN pip install --no-cache-dir -e .
COPY backend/prompts ./prompts
COPY db/migrations /srv/db/migrations
COPY config /srv/config
# 마이그레이션을 적용한 뒤 워커 1개로 띄운다(ADR-013: 대화 맥락을 메모리에 둠).
# uvicorn 접근 로그는 IP·쿼리 문자열을 남기므로 끄고, RequestLogger의 jsonl만 쓴다.
CMD ["sh", "-c", "python -m app.data.migrate && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log"]
