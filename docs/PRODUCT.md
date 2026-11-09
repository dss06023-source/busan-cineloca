# Product
<!-- impeccable:product-schema 1 -->

## Platform
web

## Users
부산을 찾은 여행객과 영화 팬. 휴대폰을 들고 걸으면서 근처 영화 촬영지를 찾고, 작품을 고르고, 반나절 코스를 짠다. 시연(11/26)은 발표자 노트북 한 대와 휴대폰으로 한다.

## Product Purpose
부산 영화·드라마 촬영지를 지도·작품·AI 탐색·코스로 찾고, 현장에서 방문을 인증해 스탬프를 모으게 한다. 공공데이터(촬영지·KMDb·KOBIS)와 AI 게이트웨이(Gemini 무료 티어, 실패 시 강등)를 쓴다.

## Positioning
부산 촬영지 공공데이터를 하나로 합친 지식베이스 위에서 "마동석 나온 영화 촬영지 중 지하철역에서 걸어서 10분 안" 같은 자연어 질문을 지도·코스로 바로 바꿔 준다.

## Operating Context
- 사용자 화면: 360px 모바일 먼저, 하단 탭 5개(지도·작품·AI 탐색·코스·내 기록). 넓은 화면(1100px 이상)의 첫 화면은 좌 AI 탐색 · 중앙 지도 · 우 작품·코스 3단으로 합친다(2026-10-27 결정).
- 관리자 화면: /admin 데스크톱 레이아웃.
- 지도는 카카오 지도 SDK. 실패하면 목록으로 대체한다.

## Capabilities and Constraints
- React + Vite + TypeScript SPA, MSW 목 응답으로 백엔드 없이 개발.
- 용어: 화면은 '촬영지', 코드는 location.
- AI가 만든 문장에는 'AI 생성' 표시, 화면마다 데이터 출처 표시(과제 필수).
- 위치 좌표는 저장하지 않는다. 스탬프·저장 코스는 브라우저에만.
- 비용 0원. 영화 이미지 파일은 저장하지 않는다(NO_STORE).

## Brand Commitments
이름 "부산 씨네로케". 그 밖의 로고·색은 DESIGN.md를 따른다.

## Evidence on Hand
- docs/build-plan.md, docs/sdd.md
- 미니 시드(db/seed/mini_seed.sql, 가짜 데이터), 목업(frontend/src/mocks/data.ts)
- 실제 사용자 후기·수치는 없다. 만들어 넣지 않는다.

## Product Principles
1. 걸으면서 한 손으로 쓴다: 지도와 거리가 먼저다.
2. AI는 도구이지 주인공이 아니다: AI 결과는 표시하고 틀릴 수 있음을 알린다.
3. 출처를 숨기지 않는다.
4. AI·외부 API가 죽어도 화면은 돈다(강등).

## Accessibility & Inclusion
한국어 UI. 키보드 조작, 대비, 지도 대신 목록 대체 경로를 유지한다.
