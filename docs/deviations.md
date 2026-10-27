# SDD와 다르게 만든 것

SDD v0.1과 다르게 구현한 점을 한 줄씩 남깁니다(AGENTS.md '기록'). 초깃값은 docs/build-plan.md 12장 표입니다.

| 항목 | SDD v0.1 | 이 문서 | 장 |
|---|---|---|---|
| 대체 체인 | Gemini → Ollama → 강등 | Gemini → 강등, Ollama는 설정으로 켬 | 1·6 |
| AI 제한 시간 | 조건 추출·구조화 10초, 요약·소개 8초(SRS FR-411·IF-09도 10초) | 요청 마감 7.5초 안에서 작업별 상한 | 6 |
| temperature | 0~0.3 | Gemini는 기본값 1.0, Ollama만 0.2 | 6 |
| 배치 환경 | 팀 서버 GPU, Cloudflare 터널, 컨테이너 6개 | 발표자 노트북, Tailscale serve, web·api·db·embed + batch 프로필 | 3 |
| 임베딩 | 팀 서버에서만 계산 | 아무 PC의 Ollama CPU, 실패하면 트라이그램만 | 1·6 |
| 폴더 | 계획서 17.2의 batch/ 최상위 | backend/app/batch, 어댑터는 data/ 아래 | 4 |
| DB | 5.2 정의 | ext_key·retired 추가, address·gu NULL 허용, leg_mode VARCHAR(6) | 7 |
| 시연 질의 문구 | 계획서 20.3 '지하철 10분 안' | SRS AC-05 '지하철역에서 걸어서 10분 안' | 2·7 |
| 용어 | 작품지·촬영지 혼용 | 촬영지(코드는 location) | 1 |
| 공통 처리 위치 | NoticeCheck·RateLimiter를 미들웨어로 | AI 라우터 의존성 `deps.ai_guard`로 둠. 의존성에서 던진 오류가 오류 처리기를 그대로 타고, AI가 아닌 경로는 아예 거치지 않음 | WP-01 |
| ERR 코드 없는 HTTP 오류 | 정의 없음 | 404·405 등은 `HTTP-<상태>` 코드로 같은 오류 형식에 담음 | WP-01 |
| ERR-016 처리 위치 | ErrorHandler | RequestLogger가 받아 500 + request_id를 돌려주고, 정제한 스택 추적은 jsonl 로그에만 남김 | WP-01 |
