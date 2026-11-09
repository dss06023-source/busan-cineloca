# AGENTS.md — 부산 씨네로케 구현 규칙

## 먼저 읽을 것
- docs/build-plan.md(제작 설계안): 맡은 WP의 행(10장)과 관련 장
- docs/sdd.md(SDD v0.1): 클래스·API·테이블 정의. 둘이 다르면 build-plan이 우선

## 범위
- 맡은 WP의 폴더만 고친다(역할별 폴더는 README '팀과 담당 폴더'). 다른 폴더를 고쳐야 하면 PR에 이유를 쓰고 그 WP 담당에게 알린다.
- 계층 규칙 api → services·pipeline → support → data를 지킨다(lint-imports가 검사).
- SQL은 backend/app/data/repositories와 db/migrations에만, httpx는 data/adapters와 data/ai_gateway에만 둔다.
- 요구사항이 모호하면 추측해서 만들지 말고 PR이나 팀 채널에서 묻는다.

## 브랜치와 PR
- 브랜치는 feature/이슈번호-작업명(fix/…, docs/…). main에 직접 push하지 않는다.
- 커밋은 Conventional Commits와 이슈 번호로 쓴다. 예: `feat: 촬영지 근접 검색 API 추가 (#21)`
- PR 하나에 변경 하나, 400줄 안팎. .github/pull_request_template.md를 채운다(요구사항 ID, 테스트 방법, 새 의존성과 라이선스, AI 사용 여부).
- CI가 통과하고 리뷰어 1명이 승인하면 squash 병합한다.

## 테스트
- 새 코드에는 테스트를 같이 넣는다. build-plan 5장의 '꼭 넣을 단위 테스트'는 빠뜨리지 않는다.
- 실패하는 테스트를 지우거나 skip·xfail로 돌리지 않는다. 기대값을 바꿔야 하면 PR에 이유를 쓴다.
- CI와 단위 테스트에서 실제 외부 API·실제 LLM을 부르지 않는다(respx, AI_PROVIDERS=fake).

## 데이터와 비밀
- 키·비밀번호·토큰 서명 키를 코드·테스트·로그·커밋에 넣지 않는다. 저장소 루트 .env.example에는 이름만 적는다.
- NO_STORE 데이터(카카오 응답, KOBIS 응답 본문, 영화 이미지 파일)는 DB·캐시·파일·로그·픽스처에 저장하지 않는다. 필요하면 손으로 만든 가짜를 backend/tests/fixtures/fake/에 둔다.
- 사용자 위치 좌표와 마스킹 전 입력은 로그에 남기지 않는다. 로그는 PrivacyGuard.scrub()을 거친다.
- 외부 API 응답 필드를 추측하지 않는다. 저장 가능한 실제 응답 사본을 backend/tests/fixtures/real/에 먼저 넣고 parse()를 쓴다.

## AI 코드
- LLM은 SQL·코드를 만들지 않는다. LLM 출력은 스키마 검증을 거쳐 템플릿 매개변수로만 쓴다.
- 모델명·제한 시간·공급자 순서는 config/ai.yaml(저장소 루트)에만 둔다.
- 프롬프트를 바꾸면 backend/prompts/<작업>.v<번호>.md의 번호를 올리고 평가셋 결과를 PR에 붙인다.

## 의존성
- 새 라이브러리는 MIT·BSD·Apache-2.0 같은 허용 라이선스만 쓴다. GPL·AGPL은 넣지 않는다.

## 기록
- SDD와 다르게 만들었으면 docs/deviations.md에 무엇을 왜 바꿨는지 한 줄을 추가한다.
