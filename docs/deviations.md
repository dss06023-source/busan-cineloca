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
| 시드 내보내기 | pg_dump 전체(스키마 포함) | 데이터만 내보내고(`--data-only --on-conflict-do-nothing`), 적재할 때 마이그레이션으로 스키마를 먼저 만든다. 스키마의 기준을 마이그레이션 하나로 둠 | WP-02 |
| 미니 시드 | 실제 원본 응답에서 고른 20곳 | 작업 환경에서 공공 API에 닿지 않아, 실제 장소 이름 + 근사 좌표 + 지어낸 작품·인물로 만든 개발용 시드(source `DEV-SEED`). 키 발급 뒤 실제 응답으로 교체 | WP-02 |
| GeminiProvider API | Interactions API(`/v1beta/interactions`, `response_format`, `output_text`) | 안정 API `models/{model}:generateContent`(`responseMimeType`·`responseJsonSchema`·`thinkingConfig.thinkingLevel`). 작업 환경에서 Interactions 문서를 확인할 수 없었음. 키를 받으면 실호출 1회로 확인하고, 바꾸려면 이 클래스만 고친다 | WP-06 |
| 마스킹 위치 | LLMClient 안 | 부른 쪽(services)이 `PrivacyGuard.mask_inputs()`로 마스킹한 입력을 넘긴다. 계층 규칙상 data/ai_gateway가 support를 import할 수 없음 | WP-06 |
| 상태 확인의 차단기 상태 | app.state.ai_breakers 딕셔너리 | `app.state.llm.breaker_states()`를 매번 읽음 | WP-06 |
| 스포일러 단계 값 | API-004 {spoiler: none·partial} | 그대로 두되, build-plan의 "'일부' 단계 제거(④)"는 SRS FR-108의 두 단계(없음·일부)를 뜻하는 것으로 읽음 | WP-08 |
| 미니 시드의 KMDb 항목 | KMDb는 ID_ONLY라 work.kmdb를 채우지 않음 | 개발용 가짜 줄거리·키워드를 work 1·3·9의 kmdb에 넣음(source DEV-SEED). 실데이터 적재 때는 정책을 따름 | WP-08 |
| API-002 응답 | {work, people, plot, images, vod, locations, related, source_ids} | keywords·kmdb_link·sources를 더함. images는 {posters, stills} 주소 목록 | WP-08 |
| API-004 응답 | {status, sentences, degraded, fallback, source_ids} | ai_generated·dropped_count·sources를 더함. 강등 fallback은 SRS UC-02 3b대로 두 단계 모두 원문 줄거리와 촬영지 목록 | WP-08 |
| 계층 계약 | services와 pipeline이 같은 층(서로 import 금지) | api → services → pipeline → support → data. build-plan 4장대로 services가 pipeline의 공용 부품(QueryPipeline·RoutePlanner)을 씀 | WP-09 |
| API-013 입력 | {text} | {text, here?}. 기준이 '현재 위치'일 때만 브라우저 좌표를 받고 저장·기록하지 않음 | WP-09 |
| API-013 응답 | {status, chips, choices, items, summary, relaxed, masked, prefill} | notices(사전에 없어 뺀 조건), criteria·labels(칩 삭제·선택 뒤 API-014로 다시 검색), works(result_type WORK), source_ids·sources를 더함 | WP-09 |
| 기준 없는 '걸어서 N분' | 정의 없음 | 기준 위치 없이 도보 조건만 있거나 기준 역 이름이 '지하철역'처럼 일반 명사면 '아무 역에서 걸어서 N분'(T3)으로 봄. 기준만 있고 이동 조건이 없으면 반경 1km | WP-09 |
| API-014 입력 | {conditions} | {criteria, labels}. criteria는 API-013 응답의 criteria와 같은 모양 | WP-09 |
| 방문 순서 계산 | NearestNeighbor2Opt | 장소 9곳 이하는 동적 계획법(Held-Karp)으로 정확해, 10곳 이상은 최근접 이웃 + 2-opt + Or-opt. 무작위 시험에서 2-opt만으로는 8곳 이하 +10% 목표(AI-REQ-11)를 넘는 배치가 있었음 | WP-10 |
| 추천 코스 상세 | course_stop의 leg_* 저장값 표시 | API-010이 저장된 순서로 구간을 매번 다시 계산(역간 시간이 바뀌어도 맞음). leg_* 열은 쓰지 않음 | WP-10 |
| API-012 입력·응답 | {preference 또는 manual, start, budget_h} → {status, preference, route, reasons, intro, masked} | status에 FALLBACK·OUT_OF_SCOPE·INFEASIBLE, reason(budget·candidates), notices를 더함. start·budget_h는 선택이며 주면 문장보다 우선(FR-308), 없으면 문장의 출발지, 그것도 없으면 부산역 | WP-10 |
| 구간 거리 | 정의 없음 | 직선거리 × 1.3(도시철도 구간 포함). total_m은 그 합 | WP-10 |
