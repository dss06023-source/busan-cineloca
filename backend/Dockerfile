FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml ./
COPY app ./app
# 편집 가능 설치: 코드가 /srv에 남아 migrations·config·prompts를 상대 경로로 찾는다
RUN pip install --no-cache-dir -e .
COPY migrations ./migrations
COPY config ./config
COPY prompts ./prompts
# 마이그레이션을 적용한 뒤 워커 1개로 띄운다(ADR-013: 대화 맥락을 메모리에 둠).
# uvicorn 접근 로그는 IP·쿼리 문자열을 남기므로 끄고, RequestLogger의 jsonl만 쓴다.
CMD ["sh", "-c", "python -m app.data.migrate && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log"]
