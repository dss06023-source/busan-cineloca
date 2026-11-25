### WBS 번호

5.2

### 관련 요구사항·설계 ID

NFR-017, FR-615, ADR-009, SDD 2.4

### 목적

`.env.example`을 복사해 `.env`를 만들면, 값이 빈 줄의 같은 줄 설명(`GEMINI_DAILY_LIMIT=          # 비우면 20…`)을 docker compose가 값으로 읽는다. 그래서 api 컨테이너 안에서 다음 값들이 설명 글이 된다.

- `GEMINI_DAILY_LIMIT`: `int()` 오류가 나서 "AI 설정이 올바르지 않아 AI 없이 시작" 상태로 AI가 통째로 꺼진다.
- `GEMINI_MODEL`, `OLLAMA_*`
- `ADMIN_PASSWORD_HASH`: 비워 두면 503이어야 하는데 '형식 틀림'이 된다.
- `STAMP_SIGNING_KEY`

이 현상은 2026-11-25 팀원 PC(Docker Compose v2)와 `docker compose config`(v5.6.1)에서 재현했다. 값이 있는 줄(`AI_PROVIDER=gemini   # …`)은 정상이다. Vite(dotenv)와 배치의 `load_env_file`은 이 경우를 주석으로 처리해서 compose에서만 생긴다.

### 작업 내용

- [ ] 값이 빈 줄의 설명을 윗줄 주석으로 옮기기
- [ ] 같은 형식이 다시 들어오지 않게 테스트 추가

### 완료 조건

`.env.example`을 그대로 복사해 `docker compose config`를 돌렸을 때 빈 칸 값이 모두 `""`로 나온다

### 담당 역할

R1
