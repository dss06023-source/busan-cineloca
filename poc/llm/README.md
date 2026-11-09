# LLM PoC (TBD-05)

## Gemini 조건 추출 실제 호출

확인일: 2026-10-27. 클라우드 개발 환경에서 GeminiProvider(generateContent)로 1회 호출했습니다.

| 항목 | 값 |
|---|---|
| 모델 | gemini-3.5-flash-lite (`config/ai.yaml`) |
| 작업 | extract_query (프롬프트 `backend/prompts/extract_query.v1.md`) |
| 출력 검증 | `config/schemas/conditions.v1.json` 통과 |
| 응답 시간 | 1.91초 (작업 상한 3.0초, 요청 마감 7.5초) |

## 남은 확인

- qwen3:8b(Ollama)와의 품질 비교: 평가셋(`eval/`)의 기대값을 사람이 확정한 뒤 같은 입력으로 비교합니다.
- Gemini 무료 한도: AI Studio에서 분당·하루 한도 숫자를 확인해 `config/ai.yaml`의 rpm·daily_limit에 넣습니다(지금 값 10·1000은 임시).
