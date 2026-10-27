**소프트웨어 설계 명세서**

Software Design Document (SDD)

문서 코드: SDD

| **프로젝트명** | 부산 씨네로케 (Busan CineLoca) — 영화·드라마 속 부산 촬영지 AI 안내 서비스 |
|----------------|----------------------------------------------------------------------------|
| **팀명**       | \[팀명 입력\]                                                              |
| **팀원**       | \[이름 / 학번 / 역할\] × 4 (역할 R1~R4는 계획서 16장)                      |
| **버전**       | v0.1 (초안)                                                                |
| **작성일**     | 2026-10-24                                                                 |
| **담당교수**   | 임한신                                                                     |

소프트웨어공학(01CSE307) 팀 프로젝트 · 중간 산출물

# 문서 관리

| **버전** | **날짜**   | **작성자** | **변경 내용**                                                                                                                                                                                        |
|----------|------------|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0.1      | 2026-10-24 | \[작성자\] | 초안: SRS v0.1(기능 85개·비기능 20개·AI 15개)을 바탕으로 컴포넌트 15개·ADR 14개, 클래스 다이어그램 6개·시퀀스 4개·액티비티 1개, 테이블 16개, API 25개, 오류 16개, 추적표 작성. AI 활용 범위는 부록 C |
| 0.2      | \[날짜\]   | \[작성자\] | \[팀 인스펙션(10/26)과 10주차 상세 설계·디자인 패턴 강의 내용 반영\]                                                                                                                                 |
| 1.0      | \[날짜\]   | \[작성자\] | 최종본                                                                                                                                                                                               |

# 목차

\[목차\] Word에서 열 때 필드 업데이트에 예를 누르거나, 여기를 클릭하고 F9를 누르면 목차가 만들어집니다.

# 1. 설계 개요 (Design Overview)

## 1.1 목적 및 범위

이 문서는 SRS v0.1의 요구사항을 '부산 씨네로케'에서 어떻게 실현할지 정합니다. 강의 6주차의 구분에 따라 아키텍처 설계(2~3장: 구성요소와 책임, 인터페이스, 상호관계)와 상세 설계(4~11장: 클래스, 상호작용, 데이터, API, 알고리즘)로 나눠 적고, 12장 추적표로 요구사항과 연결합니다.

- **범위**: Must 요구사항(기능 77개, 비기능 17개, AI 15개)은 클래스·API·테이블 수준까지 설계했습니다. Should(FR-305·616·801~803, NFR-014·020)는 API와 클래스까지, Could(FR-901~903, NFR-019)는 확장 지점만 정했습니다. 화면은 SRS 6장(UI-01~12)을 따릅니다.

- **완성도**: 중간 평가 대상인 1~3장은 v0.1에서 확정하고, 4~11장은 10주차(상세 설계·디자인 패턴) 강의 뒤 v0.2에서 보완합니다.

- **추적성 원칙**: 주요 설계 요소에는 관련 SRS 요구사항 ID(FR/NFR/AI-REQ)를 명시합니다. 설계 요소 ID는 SRS 10장과 같은 것을 씁니다.

설계 요소 ID 규칙은 다음과 같습니다.

- COMP-01~15 컴포넌트(3장, SRS 10장과 같음), ADR-001~014 아키텍처 결정(2.2), API-001~025(6장), ERR-001~016(8장)

- CD-01~06 클래스 다이어그램(4.1), SD-01~04 시퀀스 다이어그램(4.2), AD-01 액티비티 다이어그램(4.3), ERD-01 데이터 모델(5.1)

- 테스트 케이스는 SRS 10장 규칙(FR-101 → TC-101, NFR-001 → TC-N01, AI-REQ-01 → TC-A01)을 따릅니다.

## 1.2 관련 문서

- SRS v0.1(2026-10-23): 요구사항, 업무 규칙 BR-01~15, 유스케이스 UC-01~20(상세 명세 UC-02·05·09·10, 나머지 상세 흐름은 저장소 docs/srs/uc_specs_full.md), 외부 인터페이스 IF-01~12, 데이터 DATA-01~12, 인수 기준 AC-01~17

- 프로젝트 계획서 v0.2: 9장 AI 활용 계획, 10장 개인정보·저작권, 11장 시스템 구성과 ADR-001~010, 17장 GitHub·형상관리, 18장 품질 보증·테스트

- 강의 자료: 5주차 SW 모델링(UML), 6주차 아키텍처 설계

- 외부 문서: 공공데이터포털·KMDb·KOBIS·행정안전부 주소·TourAPI 명세, 카카오 지도 JavaScript SDK, Google Gemini API, Ollama API, PostgreSQL·pgvector 문서

## 1.3 설계 목표 및 품질 속성

강의 6주차의 품질 속성(보안성, 가용성, 변경용이성, 성능, 사용편의성)에 이 서비스에 필요한 개인정보·이용조건 준수, 시험 용이성, 이식성을 더했습니다.

| **품질 속성** | **목표**                                                                                    | **설계 대응**                                                                                                                                                                                                  | **관련 NFR**              |
|---------------|---------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------|
| 성능          | 동시 10명에서 지도·검색·코스 계산 p95 2초, AI 응답 p95 8초                                  | 지식베이스 선적재(ADR-005), 위경도 GiST 색인(ADR-011), 역간 소요시간 사전 계산(station_time), 요청당 외부 AI 호출 최대 2회, AI 응답 캐시 24시간, KOBIS 등급은 별도 API(API-003)로 분리해 상세 화면을 막지 않음 | NFR-001, NFR-006, NFR-014 |
| 가용성        | AI 장애에도 지도·필터 검색·인증·작품 상세는 정상, AI 기능은 강등 응답 100%. 재시작 5분 이내 | AI 없는 경로(COMP-04·07은 COMP-08을 쓰지 않음), 대체 체인·차단기·강등 응답(COMP-08), 컨테이너 자동 재시작, 시드 백업                                                                                           | NFR-002, NFR-020          |
| 보안          | 키 유출 0건, SQL·지시 주입 성공 0건, 위조 토큰 거부 100%                                    | 검색 템플릿(ADR-010), 입력 스키마 검증, HMAC 서명 토큰(ADR-009), 비밀키는 환경변수, HTTPS 전용                                                                                                                 | NFR-009~012               |
| 개인정보      | 위치·입력 원문 저장 0건                                                                     | 외부 AI 앞 마스킹(COMP-10), 위치는 POST 본문으로 요청 중에만 사용, 서버는 스탬프를 저장하지 않음, 로그 정제                                                                                                    | NFR-003, AI-REQ-03        |
| 이용조건 준수 | NO_STORE 데이터 저장 0건, 출처 표시율 100%                                                  | 어댑터가 저장 정책을 강제(ADR-004), CI 스키마 검사, 출처 카드를 표현 계층 한 곳에서 붙임(ADR-014)                                                                                                              | NFR-007, NFR-008          |
| 변경용이성    | 공급자·저장 정책 교체는 설정 변경만                                                         | 어댑터·Strategy, 설정 파일(config/ai.yaml, config/providers.yaml), 의존성 주입                                                                                                                                 | NFR-015, AI-REQ-14        |
| 시험 용이성   | 핵심 모듈 커버리지 70%                                                                      | 계층 분리와 의존성 주입으로 가짜 어댑터 사용, 알고리즘은 외부 의존이 없는 클래스(Geofence, NearestNeighbor2Opt, GroundingVerifier, PrivacyGuard, WorkMatcher)로 분리                                           | NFR-016                   |
| 사용편의성    | 외부 사용자 과업 성공률 80%, 첫 화면 3초                                                    | 지도 홈에서 바로 근접 검색, AI 실패 시 같은 화면에서 필터 패널, 해석 조건 칩으로 수정·취소(강의 6주차 '오류 복구')                                                                                             | NFR-013, NFR-014          |
| 이식성        | docker compose up 한 번과 시드 적재로 10분 안에 실행                                        | Docker Compose, seed.sql.gz, AI_PROVIDER 설정                                                                                                                                                                  | NFR-017                   |

# 2. 시스템 아키텍처 (System Architecture)

## 2.1 전체 아키텍처

<img src="media/image1.png" style="width:6.69291in;height:5.2874in" />

그림 1. 컴포넌트 다이어그램(전체 아키텍처) — 계층과 컴포넌트, 제공 인터페이스, 의존 관계

시스템은 Client-Server 3계층이고, API 서버는 다시 네 계층으로 나뉩니다. 촬영지·작품 데이터는 별도 프로세스인 배치(COMP-13)가 미리 적재하고, API 서버와 배치는 같은 PostgreSQL을 공유합니다.

- **계층**: 표현(COMP-02) → 업무(COMP-03~07·14) → 공통 지원(COMP-09·10·15) → 데이터 접근(COMP-08·11·12) 순서로 아래 방향으로만 호출합니다. 외부 AI를 부르는 COMP-08은 외부 시스템과 통신하므로 데이터 접근 계층에 두었습니다.

- **AI 없는 경로**: 지도 탐색(COMP-04), 방문 인증(COMP-07), 필터 패널 검색(QueryService.search)은 AI를 거치지 않아 외부 AI가 멈춰도 동작합니다(NFR-002).

- **AI 단일 경로**: 외부 AI 호출은 업무 서비스 → 마스킹(COMP-10) → LLMClient(COMP-08) → 근거 대조(COMP-09)의 한 길로만 나갑니다.

- **외부 의존 격리**: 외부 데이터 API는 COMP-11, 외부 AI는 COMP-08, DB는 COMP-12만 접근합니다. 업무 계층은 인터페이스만 압니다(강의 6주차 Wrapper/Adapter로 외부 의존을 한 곳에 집중).

- 카카오 지도는 브라우저에서만 쓰고 서버는 카카오 응답을 받지도 저장하지도 않습니다(DATA-07 NO_STORE).

## 2.2 아키텍처 스타일 및 선택 이유

강의 6주차의 아키텍처 스타일 8가지를 검토해 네 가지를 조합했습니다.

- **채택**: 클라이언트-서버(3계층, ADR-001), 계층형(API 서버, ADR-002), 파이프-필터(AI 처리와 배치, ADR-003), 데이터 중심 Repository(배치·API·관리 기능이 지식베이스를 공유, ADR-005·012)

- **제외**: 이벤트 기반(실시간 이벤트가 없고 주 1회 배치와 1분 폴링이면 충분해 브로커를 운영할 이유가 없음), MVC(서버는 JSON API만 제공하고 화면은 React SPA가 담당), Peer-to-Peer(사용자 간 공유 요구 없음), 마이크로커널(플러그인 확장 요구가 없고 공급자 교체는 Strategy와 설정으로 충분)

ADR-001~010은 계획서 11.1의 결정을 이어받았고, ADR-011~014는 설계 단계에서 추가했습니다.

| **결정 ID** | **선택**                                                                                                         | **이유**                                                                                    | **대안/Trade-off**                                                                                                               | **관련 요구사항**                |
|-------------|------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|----------------------------------|
| ADR-001     | Client-Server 3계층(React SPA ↔ FastAPI ↔ PostgreSQL)                                                            | 화면과 업무 로직 분리, 역할 분담, API 키를 브라우저에 두지 않음, 데이터 중앙 관리           | 대안: 브라우저에서 외부 API 직접 호출(키 노출·약관 위반). 서버 장애 시 전체 중단 → 자동 재시작, 브라우저 저장 데이터는 계속 보임 | NFR-009, NFR-020                 |
| ADR-002     | API 서버 계층형(표현 → 업무 → 공통 지원 → 데이터 접근, 아래 방향 호출만)                                         | 관심사 분리, 계층별 시험, 외부 변경 영향을 데이터 접근 계층에 가둠                          | 대안: 라우터에서 DB·API 직접 호출(코드는 적지만 시험·교체가 어려움). 계층 수만큼 코드 증가                                       | NFR-015, NFR-016                 |
| ADR-003     | AI 처리와 배치는 파이프-필터(단계마다 같은 문맥 객체)                                                            | 단계별 시험·교체, 근거 게이트로 생성 차단, '단순 LLM 호출이 아님'을 구조로 보장             | 대안: 서비스 메서드 안 순차 호출(단계 경계가 흐려짐). 문맥 객체 형식 고정, 단계 지연 누적 → 요청 마감 시간 관리                  | AI-REQ-01, AI-REQ-04             |
| ADR-004     | 외부 API는 어댑터, AI 공급자는 Strategy + 대체 체인, 공급자마다 저장 정책                                        | 약관 차이를 한 곳에서 강제, 공급자 교체는 설정만 변경                                       | 대안: SDK 직접 호출(교체 비용 큼). 추상화 코드 증가                                                                              | NFR-007, NFR-015, AI-REQ-02      |
| ADR-005     | 촬영지·작품 데이터는 배치로 지식베이스에 선적재                                                                  | 응답 속도, 호출 한도 절약, 장애 격리, 같은 데이터로 재현 가능한 시험                        | 대안: 요청마다 공공 API 호출(느리고 한도 초과). 데이터가 배치 주기(주 1회)만큼 늦음                                              | NFR-001, NFR-018                 |
| ADR-006     | 저장용 좌표는 행정안전부 주소 API, 카카오는 지도 표시 전용                                                       | 카카오 응답은 저장 금지                                                                     | 대안: 카카오 좌표 변환(약관 위반). 좌표계 변환과 주소 없는 장소의 수동 보정 필요                                                 | FR-605, NFR-007                  |
| ADR-007     | 영화 정보는 KMDb 주 + KOBIS 실시간 보조(TMDB 제외), KMDb 저장 정책은 설정값                                      | TMDB는 AI 앱 연계 금지, KOBIS는 저장 금지                                                   | KMDb가 ID_ONLY로 정해지면 상세 조회가 실시간 호출로 바뀌어 지연 증가(TBD-01)                                                     | FR-103, FR-107, FR-604           |
| ADR-008     | PostgreSQL 하나에 관계형 + pgvector + pg_trgm                                                                    | 운영 대상이 하나, 데이터 일관성, 퍼지·벡터 검색을 같은 질의에서 사용                        | 대안: 별도 벡터 DB(운영 대상 증가). 대규모 벡터에는 한계(이 시스템은 수천 건)                                                    | FR-403, FR-617                   |
| ADR-009     | 방문 인증은 서버 지오펜스 + HMAC 서명 토큰, 서버는 위치·스탬프를 저장하지 않음                                   | 개인정보 최소화, 로그인 없이 위조 방지                                                      | 대안: 회원 DB에 스탬프 저장(개인정보 증가). 기기를 바꾸면 스탬프가 사라짐(FR-509로 고지)                                         | FR-502, FR-504, NFR-003, NFR-011 |
| ADR-010     | LLM은 SQL을 만들지 않고 검색 템플릿(T1~T4)의 매개변수만 채움                                                     | SQL 삽입·환각 방지, 결과의 결정성                                                           | 대안: Text-to-SQL. 표현할 수 있는 질의가 템플릿 범위로 제한 → 조건 완화·필터 패널로 보완                                         | FR-404, AI-REQ-05, NFR-010       |
| ADR-011     | 근접 검색은 PostgreSQL 확장(cube·earthdistance)과 GiST 색인, PostGIS는 쓰지 않음                                 | 촬영지 수백 곳 규모는 반경 검색이면 충분, PostGIS(GPL)는 계획서 10.4의 라이선스 규칙에 걸림 | 대안: PostGIS(다각형·경로 질의). 구·군 경계 질의를 못 함 → 구·군은 주소 필드로 처리                                              | FR-203, NFR-001                  |
| ADR-012     | 배치는 별도 프로세스, 스테이징에 적재해 건수 가드를 통과하면 한 트랜잭션으로 교체, API와는 DB(sync_run)로만 통신 | 동기화가 실패해도 서비스 데이터 유지, API 서버와 결합 없음                                  | 대안: API 서버 안 백그라운드 작업(장애가 서로 번짐). 수동 동기화가 최대 1분 늦게 시작                                            | FR-612, FR-613, BR-14            |
| ADR-013     | 캐시 서버를 따로 두지 않음: AI 응답 캐시·호출 수는 PostgreSQL, F4 대화 맥락·로그인 실패 횟수는 API 서버 메모리   | 컨테이너 수를 줄여 팀원 PC와 시연 환경을 단순하게                                           | 대안: Redis. API 워커를 1개로 제한해야 하고 재시작하면 맥락이 지워짐(맥락은 30분짜리라 허용)                                     | FR-408, FR-615, AI-REQ-15        |
| ADR-014     | 업무 서비스는 출처 ID만 돌려주고 출처 카드는 표현 계층(COMP-02)이 한 곳에서 붙임                                 | 출처 표시율 100%를 한 지점에서 보장, 서비스와 COMP-15 사이 결합 제거                        | 대안: 서비스마다 출처 조립(누락 위험). 모든 응답 스키마에 source_ids 필수                                                        | FR-704, NFR-008                  |

# 3. 컴포넌트 설계 (Component Design)

강의 5주차 컴포넌트 다이어그램 작성 과정(단위 결정 → 컴포넌트 식별 → 책임·인터페이스 정의 → 의존 관계 정의)을 따랐습니다. 단위는 기능(F1~F5, C1)과 공통 관심사(AI 호출, 근거 검증, 개인정보, 출처, 데이터 접근)입니다.

| **ID**  | **컴포넌트**                | **책임**                                                                                                                                | **입력**                        | **출력**                           | **의존성**                             | **관련 요구사항**                                           |
|---------|-----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|---------------------------------|------------------------------------|----------------------------------------|-------------------------------------------------------------|
| COMP-01 | Web Client (React SPA)      | 화면 UI-01~12, 위치·정확도 수집, 카카오 지도·묶음 마커, 브라우저 저장(토큰·코스·즐겨찾기), 이용 안내 확인, AI 실패 시 필터 패널 전환    | 사용자 조작, 위치, API 응답     | HTTP 요청, 화면                    | COMP-02, 카카오 지도 SDK, 브라우저 API | FR-201·204·208, FR-306, FR-701·706, FR-801, NFR-004·013·014 |
| COMP-02 | API Server (FastAPI 라우터) | 엔드포인트(6장), 입력 검증, 세션 ID·이용 안내 확인, 관리자 인증, 속도 제한, 응답 조립(출처 카드·'AI 생성'), 오류 표준화(8장), 요청 로그 | HTTP 요청                       | JSON 응답                          | COMP-03~07·14·15, COMP-10              | FR-401, FR-615, FR-704·707, NFR-005·010                     |
| COMP-03 | Archive Service             | 작품 목록·상세, KOBIS 등급 실시간 조회, 스포일러 단계별 근거 묶음, AI 소개 생성·검증·강등·캐시                                          | 검색 조건, 작품 ID, 근거 정책   | WorkDetail, Rating, IntroResult    | COMP-08·09·11·12                       | FR-101~111, FR-802                                          |
| COMP-04 | Map Service                 | 기준 위치 반경 검색(500m·1km·3km), 장르·연도·구·군 필터, 촬영지 상세, 구·군 통계                                                        | 기준점(요청 중에만), 반경, 필터 | LocationHit\[\], LocationDetail    | COMP-12                                | FR-201~210, FR-803, NFR-001                                 |
| COMP-05 | Course Service              | 추천 코스 조회, 나만의 코스 경로, AI 맞춤 코스(구조화 → 점수화 → 경로 → 예산 맞춤 → 소개), RoutePlanner 제공                            | 출발지, 장소, 취향 문장         | Route, AICourseResult              | COMP-08·09·10·12                       | FR-301~313, AI-REQ-11                                       |
| COMP-06 | Query Service               | F4 파이프라인 9단계, 필터 패널 검색, 세션 맥락(최근 3턴)                                                                                | 질의, 세션 ID, 필터 조건        | QueryResult                        | COMP-08·09·10·12                       | FR-401~412, AI-REQ-05·09·10                                 |
| COMP-07 | Stamp Service               | 지오펜스 판정, 스탬프·배지 토큰 서명·확인, 중복·인증 제외 처리                                                                          | 촬영지 ID, 위치·정확도, 토큰    | 토큰, 판정 결과                    | COMP-12                                | FR-501~509, NFR-011                                         |
| COMP-08 | AI Gateway                  | LLMClient·Embedder 제공, 작업별 프롬프트·스키마, 대체 체인(Gemini → Ollama), 스키마 검증·1회 재요청, 차단기, 캐시, 호출 수              | 작업, 입력, 마감 시간           | LLMResult 또는 AIUnavailable, 벡터 | Gemini API, Ollama, COMP-12            | AI-REQ-02·04·14·15, NFR-002·005·006                         |
| COMP-09 | Grounding Verifier          | 근거 게이트, 문장별 인명·작품명·장소명·연도·시간 수치 대조, 결말·반전 표현 검사                                                         | 문장, 근거 묶음                 | 검증된 문장, 삭제 수               | COMP-12(사전)                          | FR-110·111, FR-311, FR-407, AI-REQ-01·06·07                 |
| COMP-10 | Privacy Guard               | 입력 마스킹(전화번호·이메일·주민등록번호·카드번호), 로그 레코드 정제                                                                    | 원문, 로그 레코드               | MaskedText, 정제한 레코드          | \-                                     | FR-702, NFR-003, AI-REQ-03                                  |
| COMP-11 | Provider Adapters           | 외부 데이터 7종 클라이언트(페이지 반복·재시도·응답 형식 검사·호출 한도), 저장 정책 적용, MovieInfoProvider·RatingProvider 제공          | 요청 조건                       | 저장 가능한 항목만 담은 레코드     | 외부 데이터 API                        | FR-601·603~605, FR-703, NFR-018                             |
| COMP-12 | Knowledge Base              | Repository 10종, 검색 템플릿(T1~T4), 근접·퍼지·벡터 검색, 캐시·호출 수 저장                                                             | 조회 조건                       | 엔티티·DTO                         | PostgreSQL + pgvector                  | FR-403·404, FR-617, NFR-001                                 |
| COMP-13 | Ingest Batch                | 동기화 11단계, 스테이징·건수 가드·교체, 리포트, 정기·요청 실행                                                                          | 시간 트리거, sync_run 요청      | 적재 데이터, sync_run              | COMP-08·11·12                          | FR-601~608, FR-611~613·616·617                              |
| COMP-14 | Admin Service               | 검수 큐 처리, 촬영지 속성 편집, 추천 코스 후보·승인, 동기화 요청·리포트                                                                 | 관리자 요청                     | 처리 결과                          | COMP-05(RoutePlanner), COMP-12         | FR-609·610, FR-614                                          |
| COMP-15 | Source Registry             | 출처 ID → 출처 카드, 출처 대장·라이선스 목록                                                                                            | 출처 ID                         | SourceCard\[\], 출처 대장          | COMP-12                                | FR-704·705, NFR-008                                         |

## 3.1 계층적 상세화

강의 6주차 '아키텍처의 계층적 상세화'에 따라 컴포넌트를 하위 모듈로 나눴습니다. COMP-01·02의 모듈은 이 표가 상세 설계이고, 나머지는 4.1 클래스 다이어그램에서 상세화합니다.

| **컴포넌트**       | **하위 모듈(클래스)**                                                                                                                                                                                                                                                                                                                           | **상세 설계**  |
|--------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------|
| COMP-01 Web Client | MapView(지도·묶음 마커, 카카오 로고 유지), WorkPages(UI-03·04), AskPage(UI-05, FilterPanel), CoursePages(UI-06·07), RecordPage(UI-08: StampBook·CourseStore·FavoriteStore), SourcesPage(UI-09), AdminPages(UI-10~12), NoticeGate(첫 방문 안내), AiLabel('AI 생성' 표시), GeoProbe(위치·정확도, 5초 제한), ApiClient(OpenAPI 스키마로 만든 타입) | 이 표, SRS 6장 |
| COMP-02 API Server | Routers(자원별 라우터), Schemas(Pydantic 입력·출력), SessionHeader(X-Session-Id), NoticeCheck(X-Notice-Version), AdminAuth(쿠키 세션, 5회 실패 잠금), RateLimiter(세션당 AI 요청 분당 5회), ResponseAssembler(출처 카드·ai_generated 조립), ErrorHandler(ERR 코드), RequestLogger(PrivacyGuard로 정제 후 기록)                                  | 이 표, 6·8장   |
| COMP-03·04·07      | ArchiveService, EvidencePolicy(NoSpoilerEvidence·PartialSpoilerEvidence), MapService, StampService, Geofence, TokenSigner                                                                                                                                                                                                                       | CD-01          |
| COMP-05            | CourseService, CandidateScorer, BudgetFitter, RoutePlanner(NearestNeighbor2Opt), TravelTimeEstimator, CourseNarrator                                                                                                                                                                                                                            | CD-02, AD-01   |
| COMP-06            | QueryService, SessionStore, QueryPipeline, QueryStep 구현 9개                                                                                                                                                                                                                                                                                   | CD-03          |
| COMP-08·09·10      | ProviderChain(LLMClient), GeminiProvider·OllamaProvider, OllamaEmbedder, CircuitBreaker, PromptRegistry, SchemaValidator, GroundingVerifier, EntityLexicon, PhraseFilter, PrivacyGuard                                                                                                                                                          | CD-04          |
| COMP-11·12·15      | BaseApiClient와 하위 클래스 6개, PolicyGuard, Repository 10종, SearchTemplates, SourceRegistry                                                                                                                                                                                                                                                  | CD-05          |
| COMP-13·14         | SyncScheduler, SyncJob, IngestStep 구현 11개, WorkMatcher, AdminService                                                                                                                                                                                                                                                                         | CD-06          |

## 3.2 인터페이스

컴포넌트가 외부에 제공하는 기능의 계약입니다(강의 5주차 제공·요구 인터페이스). 업무 계층은 아래 인터페이스에만 의존하고, 구현은 FastAPI 의존성 주입(Depends)으로 연결합니다.

| **인터페이스**                     | **제공** | **사용**                      | **주요 연산**                                                                                     | **관련 요구사항**  |
|------------------------------------|----------|-------------------------------|---------------------------------------------------------------------------------------------------|--------------------|
| REST API                           | COMP-02  | COMP-01                       | API-001~025(6장)                                                                                  | 전체               |
| ArchiveService                     | COMP-03  | COMP-02                       | list_works, get_work, get_rating, get_intro                                                       | FR-101~111         |
| MapService                         | COMP-04  | COMP-02                       | search, get_location, district_stats                                                              | FR-201~210, FR-803 |
| CourseService                      | COMP-05  | COMP-02                       | list_recommended, get_course, plan_custom, plan_ai, plan_from_preference                          | FR-301~313         |
| RoutePlanner                       | COMP-05  | COMP-05, COMP-14              | plan(start, stops, fixed_order)                                                                   | FR-304, FR-614     |
| QueryService                       | COMP-06  | COMP-02                       | ask, search, reset                                                                                | FR-401~412         |
| StampService                       | COMP-07  | COMP-02                       | certify, verify, issue_badge                                                                      | FR-501~508         |
| AdminService                       | COMP-14  | COMP-02                       | reviews_pending, decide, update_location, draft_course, approve_course, request_sync, sync_report | FR-609·610·614     |
| LLMClient                          | COMP-08  | COMP-03·05·06·13              | generate(task, inputs, deadline_s)                                                                | AI-REQ-02·04       |
| Embedder                           | COMP-08  | COMP-05·06·13                 | embed(texts)                                                                                      | FR-617             |
| GroundingVerifier                  | COMP-09  | COMP-03·05·06                 | gate(evidence), verify(sentences, evidence)                                                       | AI-REQ-01·06       |
| PrivacyGuard                       | COMP-10  | COMP-02·05·06                 | mask(text), scrub(record)                                                                         | FR-702, NFR-003    |
| MovieInfoProvider · RatingProvider | COMP-11  | COMP-03·13                    | search, detail / rating(movie_cd, 3초)                                                            | FR-103, FR-107     |
| Repository 10종                    | COMP-12  | 업무 서비스, COMP-08·09·13·15 | CD-05 참고                                                                                        | FR-404, NFR-001    |
| SourceRegistry                     | COMP-15  | COMP-02                       | cards, ledger, licenses                                                                           | FR-704·705         |

## 3.3 의존 규칙과 응집도·결합도

- **호출 방향**: 위 계층만 아래 계층을 부릅니다. 업무 서비스끼리는 부르지 않으며, 예외는 COMP-14 → COMP-05의 RoutePlanner 하나입니다(UC-18 «include» UC-15를 그대로 반영).

- **외부 접근 단일화**: 외부 AI는 COMP-08만, 외부 데이터 API는 COMP-11만, DB는 COMP-12의 Repository만 접근합니다. 업무 서비스 코드에는 SQL이 없습니다. CI에서 import 규칙(import-linter)으로 검사합니다.

- **배치 분리**: 배치는 API 서버를 부르지 않고 같은 모듈(COMP-08·11·12)을 자기 프로세스에서 씁니다. 관리자의 수동 동기화 요청도 sync_run 행으로 전달됩니다(ADR-012).

강의 6주차의 응집도·결합도 유형으로 점검한 결과입니다. 약한 응집(논리적)과 스탬프 결합은 이유와 대응을 함께 적었습니다.

| **컴포넌트**        | **응집도**   | **근거**                                                       | **주요 결합** | **판단·대응**                                                                                                               |
|---------------------|--------------|----------------------------------------------------------------|---------------|-----------------------------------------------------------------------------------------------------------------------------|
| COMP-03·04·07·09·10 | 기능적       | 작품, 지도, 인증, 근거 대조, 마스킹 중 한 기능에만 기여        | 데이터 결합   | ID와 DTO만 주고받음                                                                                                         |
| COMP-05             | 교환적       | 추천·나만의·AI 맞춤 코스가 같은 Route·Location 데이터를 공유   | 데이터 결합   | 경로 계산을 RoutePlanner 인터페이스로 분리해 COMP-14와 공유                                                                 |
| COMP-06·13, COMP-02 | 순차적       | 앞 단계의 출력이 다음 단계의 입력(파이프-필터, 요청 처리 단계) | 스탬프 결합   | 단계마다 문맥 객체 전체를 받는 것은 파이프-필터의 공통 형식 비용으로 받아들이고, 단계가 읽고 쓰는 필드를 단위 테스트로 고정 |
| COMP-08             | 기능적       | AI 공급자 호출 하나에 기여(체인·차단기·캐시는 그 부속)         | 데이터 결합   | 작업 이름(Task)은 프롬프트·스키마 선택용 데이터이고 처리 흐름을 바꾸지 않음                                                 |
| COMP-14             | 논리적(약함) | '관리 기능'이라는 범주로 묶임                                  | 데이터 결합   | 기능이 적어 하나로 두되, 늘어나면 검수와 코스 관리로 나눔(v1.0 검토)                                                        |

- **제어 결합 제거**: 스포일러 단계를 플래그로 넘기면 근거 묶음 구성이 그 값으로 갈리는 제어 결합이 됩니다. 그래서 표현 계층이 단계에 맞는 EvidencePolicy 구현(NoSpoilerEvidence·PartialSpoilerEvidence)을 골라 넘기게 했습니다(강의 5주차 다형성, CD-01).

- **공통·내용 결합 회피**: 전역 변수 대신 설정 객체를 주입하고, 공유 상태는 SessionStore(COMP-06 내부)와 DB뿐입니다. 다른 컴포넌트의 내부 객체나 테이블에 직접 접근하지 않습니다.

# 4. UML 설계

## 4.1 Class Diagram

클래스는 컴포넌트 묶음별로 다이어그램 6개에 나눴습니다. 같은 이름은 같은 클래스이고, 다른 다이어그램에 정의된 클래스는 속성의 타입으로만 표시했습니다. 표기는 강의 5주차를 따릅니다: + public, - private, \# protected, 기울임 abstract, «interface», 실선 화살표 연관, 빈 마름모 집합, 채운 마름모 합성, 빈 삼각형 실선 일반화, 빈 삼각형 점선 실현, 점선 화살표 의존. 클래스 이름 위의 «1»~«11»은 파이프라인 단계 순서입니다.

### CD-01 작품·지도·방문 인증

<img src="media/image2.png" style="width:5.90551in;height:5.89346in" />

그림 2. CD-01 작품·지도·방문 인증(COMP-03·04·07)

- ArchiveService.get_intro()는 스포일러 단계를 값이 아닌 EvidencePolicy 객체로 받습니다. '없음' 단계의 NoSpoilerEvidence는 근거 묶음에서 줄거리를 뺍니다(FR-109, AI-REQ-07).

- get_rating()은 RatingProvider(KOBIS)를 3초 제한으로 부르고 결과를 저장하지 않습니다(FR-107). KMDb 정책이 ID_ONLY이면 get_work()가 MovieInfoProvider.detail()로 상세 항목을 실시간으로 가져옵니다(ADR-007).

- GeoFix는 요청 처리 중에만 존재하고 어떤 저장소에도 전달되지 않습니다. Geofence.check()는 정확도 50m 이하이고 하버사인 거리가 촬영지의 인증 반경 이하일 때만 OK입니다(BR-07).

관련 요구사항: FR-101~111, FR-201~210, FR-501~509, NFR-011, BR-06~08 관련 Use Case: UC-01~04, UC-10~12

### CD-02 코스

<img src="media/image3.png" style="width:5.11811in;height:6.96531in" />

그림 3. CD-02 코스(COMP-05)

- CandidateScorer.top_k()는 취향 일치(태그·장르·작품·인물 일치와 임베딩 유사도), 촬영 작품 수, 출발지로부터 거리를 가중합해 상위 15곳을 고릅니다. 가중치는 설정값이며 초기값은 0.6·0.2·0.2입니다(FR-309).

- BudgetFitter.fit()은 RoutePlanner로 경로를 만들고, 총 소요 시간(이동 + 체류 20분 × 장소 수)이 예산을 넘거나 8곳을 넘으면 점수가 가장 낮은 장소를 빼고 다시 계산합니다. 3곳 미만이 되면 CourseInfeasible을 냅니다(FR-310, AD-01).

- TravelTimeEstimator.leg()는 BR-12를 그대로 구현합니다. 도보는 직선거리 × 1.3 ÷ 시속 4km이고, 도보 거리가 1km를 넘으면 station_time으로 계산한 도시철도 시간과 비교해 짧은 쪽을 씁니다.

- NearestNeighbor2Opt는 최근접 이웃으로 순서를 정한 뒤 2-opt 교환을 더 줄지 않을 때까지 반복합니다. 장소가 최대 16곳(후보 15 + 출발지)이라 한 번 계산이 수 밀리초입니다(FR-304).

관련 요구사항: FR-301~313, AI-REQ-11, BR-12·13 관련 Use Case: UC-07~09, UC-15, UC-18

### CD-03 AI 대화형 탐색

<img src="media/image4.png" style="width:5.90551in;height:5.07352in" />

그림 4. CD-03 AI 대화형 탐색(COMP-06)

- QueryPipeline은 단계 9개를 정해진 순서로 실행하고, 단계는 모두 QueryContext를 받아 고친 뒤 돌려줍니다. 어느 단계에서든 status가 FALLBACK·NEEDS_CHOICE·OUT_OF_SCOPE·NOT_FOUND가 되면 이후 단계를 건너뜁니다.

- QueryService.search()(필터 패널)는 «5»~«7» 단계만 실행하므로 AI 없이 같은 검색 템플릿을 씁니다(FR-410).

- ContextMerger는 후속 질의 조건을 직전 조건에 더하고, SessionStore는 세션 ID별 최근 3턴만 30분 동안 메모리에 둡니다(FR-408, ADR-013).

관련 요구사항: FR-401~412, AI-REQ-01·05·09·10 관련 Use Case: UC-05, UC-06

### CD-04 AI 공통(AI Gateway·근거 검증·개인정보)

<img src="media/image5.png" style="width:5.90551in;height:4.15004in" />

그림 5. CD-04 AI Gateway·근거 검증·개인정보 보호(COMP-08·09·10)

- ProviderChain은 LLMClient의 유일한 구현이며, 작업별 공급자 순서를 설정에서 읽어 앞 공급자가 실패하면 다음 공급자로 넘깁니다. 공급자마다 CircuitBreaker가 있어 연속 5회 실패하면 60초 동안 건너뜁니다(AI-REQ-02).

- SchemaValidator가 JSON 스키마를 통과하지 못한 응답은 같은 공급자에 1회 다시 요청하고, 그래도 실패하면 다음 공급자로 넘깁니다(AI-REQ-04).

- GroundingVerifier.verify()는 문장마다 EntityLexicon(지식베이스의 작품·인물·장소·구·군 이름)과 연도·시간 수치 정규식으로 찾은 항목이 근거 묶음에 있는지 확인하고, 모델이 함께 낸 항목 목록도 대조합니다. PhraseFilter는 결말·반전 표현 목록(설정 파일)을 검사합니다(AI-REQ-06·07).

관련 요구사항: FR-110·111, FR-311, FR-407, FR-702, AI-REQ-01~04·06·07·14·15, NFR-002·003 관련 Use Case: UC-02, UC-05, UC-09, UC-14

### CD-05 지식베이스·외부 연동·출처

<img src="media/image6.png" style="width:5.90551in;height:4.73527in" />

그림 6. CD-05 Knowledge Base·Provider Adapters·Source Registry(COMP-11·12·15)

- BaseApiClient.fetch_all()은 템플릿 메서드입니다. 페이지 반복, 3회 재시도, 응답 형식 검사, 하루 호출 한도(daily_quota, 한도의 80%) 관리는 공통이고, 데이터별 하위 클래스는 parse()만 구현합니다(FR-601, NFR-018).

- 어댑터가 돌려주는 레코드는 PolicyGuard.storable()을 거쳐 NO_STORE 항목이 빠지고, ID_ONLY는 식별자만 남습니다. 저장소는 이 레코드만 받습니다(FR-703, BR-01).

- LocationRepository.search()는 SearchTemplates의 템플릿 4개를 조합하고 값은 모두 바인딩 매개변수로 넣습니다. 정렬 기준·결과 수(최대 20)는 허용 목록으로만 받습니다(ADR-010).

관련 요구사항: FR-403·404, FR-601~606, FR-611, FR-617, FR-703~705, NFR-001·007·018 관련 Use Case: UC-01, UC-03~06, UC-13, UC-16

### CD-06 배치·관리

<img src="media/image7.png" style="width:5.51181in;height:5.3311in" />

그림 7. CD-06 Ingest Batch·Admin Service(COMP-13·14)

- SyncJob.run()은 단계 11개를 스테이징 스키마에서 실행하고, CountGuardStep을 통과하면 publish()가 한 트랜잭션으로 서비스 테이블을 교체합니다. 실패하거나 가드를 어기면 교체하지 않고 sync_run에 이유를 남깁니다(FR-612, ADR-012).

- WorkMatcher는 작품명 유사도와 개봉연도 일치로 점수를 매겨 0.9 이상 자동 연결, 0.6 이상 검수 큐, 0.6 미만 미매칭으로 나눕니다(BR-11). SuggestAIStep의 제안은 review_item에 '미검수'로만 들어갑니다(BR-04).

- SyncScheduler는 주 1회 일정(FR-616)과 1분마다 sync_run 요청 확인을 함께 맡습니다.

관련 요구사항: FR-601~617, AI-REQ-13, BR-04·11·14 관련 Use Case: UC-16~18

## 4.2 Sequence Diagram

SRS에 상세 명세한 유스케이스 4개(UC-02·05·09·10)마다 시퀀스 다이어그램을 그렸습니다(강의 5주차 '유스케이스와 시퀀스 다이어그램의 크로스 체크'). 표현 계층(COMP-02)은 입력 검증과 응답 조립만 하므로 생략하고 메시지에 API ID를 적었습니다. 주황 라이프라인은 외부 AI 공급자, qp:QueryPipeline에서 나가는 메시지는 그 단계의 필터가 보내는 것입니다. 메시지 이름은 모두 클래스 다이어그램의 연산이며, 일치 여부는 스크립트로 확인했습니다(부록 A).

### SD-01 AI 작품 소개 보기

<img src="media/image8.png" style="width:6.49606in;height:4.89259in" />

그림 8. SD-01 AI 작품 소개 보기

관련 Use Case: UC-02 관련 요구사항: FR-108~111, FR-707, AI-REQ-01·02·06·07·12·15, NFR-006

### SD-02 AI 대화형 탐색

<img src="media/image9.png" style="width:6.29921in;height:6.60785in" />

그림 9. SD-02 AI 대화형 탐색

관련 Use Case: UC-05(UC-14 포함, UC-06 확장) 관련 요구사항: FR-401~409, FR-411·412, FR-702, AI-REQ-01~06·09·10

### SD-03 AI 맞춤 코스 받기

<img src="media/image10.png" style="width:6.49606in;height:6.02323in" />

그림 10. SD-03 AI 맞춤 코스 받기

관련 Use Case: UC-09(UC-14·UC-15 포함) 관련 요구사항: FR-302, FR-306~313, FR-702, AI-REQ-01~04·06·11

### SD-04 방문 인증하기

<img src="media/image11.png" style="width:4.33071in;height:7.40753in" />

그림 11. SD-04 방문 인증하기(UC-11 확장 포함)

저장한 코스(브라우저)는 서버에 없으므로 배지 요청에 코스의 장소 ID 목록을 함께 보내고, 추천 코스만 CourseRepository.stops()로 대상 장소를 확인합니다.

관련 Use Case: UC-10(UC-11 확장) 관련 요구사항: FR-501~506, FR-508, NFR-003·011, BR-06~09

## 4.3 기타 UML

컴포넌트 다이어그램은 2.1(그림 1), 배치 다이어그램은 10.1에 있습니다.

### AD-01 AI 맞춤 코스 생성 흐름(액티비티 다이어그램)

AI 맞춤 코스는 반복(2-opt, 예산 맞춤)과 분기(구조화 실패, 후보 부족, 소개 실패)가 많아 액티비티 다이어그램으로 따로 그렸습니다. 주황 단계만 LLM이 맡고, 장소·순서·시간은 모두 시스템이 계산합니다.

<img src="media/image12.png" style="width:4.13386in;height:6.8662in" />

그림 12. AD-01 AI 맞춤 코스 생성 흐름(FR-307~312)

관련 요구사항/Use Case: FR-307~313, AI-REQ-11, BR-12·13, UC-09, UC-15

# 5. 데이터베이스 및 데이터 설계

## 5.1 ER Diagram / Data Model

<img src="media/image13.png" style="width:6.69291in;height:4.51788in" />

그림 13. ERD-01 데이터 모델(PostgreSQL 16)

관련 요구사항: FR-101~107, FR-203~210, FR-301·302, FR-601~617, FR-703·705, NFR-001·003·005·007, AI-REQ-15

- SRS 2.7 도메인 모델의 개념을 테이블로 옮겼습니다. 스탬프·완주 배지·저장 코스·질의 세션은 서버에 저장하지 않으므로(ADR-009·013) 테이블이 없고, 5.2 표 끝에 형식만 정의했습니다.

- 정밀 위치, 입력 원문, 카카오 응답, KOBIS 응답 본문, 영화 이미지 파일은 어떤 테이블에도 없습니다. CI가 PR마다 스키마의 열 이름·형식을 검사합니다(NFR-007).

- **색인**: location은 GiST(ll_to_earth(lat, lon)), GIN(tags), GIN 트라이그램(name_norm), HNSW(embedding, 코사인). work는 GIN 트라이그램(title_norm)과 GIN(genres). dict_entry는 GIN 트라이그램(surface)과 HNSW(embedding). ai_cache는 expires_at.

- **적재**: 배치는 같은 구조의 stg 스키마에 적재한 뒤 건수 가드를 통과하면 한 트랜잭션으로 교체합니다. 관리자가 편집한 촬영지 속성(caution·cert\_\*)과 승인된 태그는 교체 때 보존합니다.

## 5.2 테이블/컬렉션 정의

| **테이블/컬렉션**     | **필드**                                                  | **타입**                                    | **PK/FK** | **Null** | **설명**                                                                              | **관련 요구사항**                  |
|-----------------------|-----------------------------------------------------------|---------------------------------------------|-----------|----------|---------------------------------------------------------------------------------------|------------------------------------|
| source                | id                                                        | VARCHAR(10)                                 | PK        | N        | 데이터 ID(DATA-01~12, SRS 7.1)                                                        | FR-611                             |
| source                | org, name, url, license                                   | TEXT                                        | \-        | N        | 제공기관, 데이터명, 원문 링크, 이용조건                                               | FR-611, FR-705                     |
| source                | policy                                                    | VARCHAR(8)                                  | \-        | N        | 저장 정책 STORE·ID_ONLY·NO_STORE                                                      | FR-703, BR-01                      |
| source                | base_date, collected_at                                   | DATE, TIMESTAMPTZ                           | \-        | Y        | 자료 기준일(출처 카드에 표시), 수집일                                                 | FR-704                             |
| work                  | id                                                        | SERIAL                                      | PK        | N        | 작품 식별자                                                                           | FR-101                             |
| work                  | title, title_norm                                         | TEXT                                        | \-        | N        | 원 제목, 정규화 제목(공백·부제 정리)                                                  | FR-102, FR-602                     |
| work                  | release_year, genres                                      | SMALLINT, TEXT\[\]                          | \-        | Y        | 개봉연도, 장르                                                                        | FR-101·102                         |
| work                  | kmdb_id                                                   | VARCHAR(20)                                 | UNIQUE    | Y        | KMDb 식별자(미매칭이면 NULL)                                                          | FR-603                             |
| work                  | kobis_movie_cd                                            | VARCHAR(10)                                 | \-        | Y        | KOBIS 영화 코드만 저장(ID_ONLY)                                                       | FR-604, FR-107                     |
| work                  | kmdb                                                      | JSONB                                       | \-        | Y        | 줄거리·키워드·포스터·스틸·예고편 주소. KMDb 정책이 STORE일 때만 채우고 ID_ONLY면 NULL | FR-103~105, TBD-01                 |
| work                  | match_status, match_score                                 | VARCHAR(10), REAL                           | \-        | N        | auto·reviewed·unmatched, 매칭 점수                                                    | FR-603, BR-11                      |
| work                  | source_id                                                 | VARCHAR(10)                                 | FK        | N        | source.id                                                                             | FR-611                             |
| person                | id, name, kmdb_person_id                                  | SERIAL, TEXT, VARCHAR(20)                   | PK        | N        | 감독·배우                                                                             | FR-103, FR-403                     |
| work_person           | work_id, person_id, role, ord                             | INT, INT, VARCHAR(8), SMALLINT              | PK·FK     | N        | 연출·출연 관계(director·actor)와 표시 순서                                            | FR-103                             |
| location              | id                                                        | SERIAL                                      | PK        | N        | 촬영지 식별자                                                                         | FR-203                             |
| location              | name, name_norm, address, gu                              | TEXT, VARCHAR(10)                           | \-        | N        | 장소명, 정규화 이름, 주소, 구·군(16개)                                                | FR-602, FR-205, BR-15              |
| location              | lat, lon                                                  | DOUBLE PRECISION                            | \-        | Y        | WGS84 좌표(주소 API). NULL이면 지도·인증에서 제외                                     | FR-605, FR-210                     |
| location              | geocode_status                                            | VARCHAR(8)                                  | \-        | N        | ok·failed·manual                                                                      | FR-613                             |
| location              | tags                                                      | TEXT\[\]                                    | \-        | N        | 승인된 장소 유형·분위기 태그만                                                        | FR-607·609, BR-04                  |
| location              | caution, safety_note                                      | VARCHAR(12), TEXT                           | \-        | Y        | none·private·residential·school, 안전 안내                                            | FR-209, FR-610                     |
| location              | cert_radius_m, cert_excluded                              | SMALLINT, BOOLEAN                           | \-        | N        | 인증 반경(기본 100, 50~300 CHECK), 인증 제외                                          | FR-502·506, BR-06·07               |
| location              | nearest_station_id, station_walk_min                      | VARCHAR(10), SMALLINT                       | FK        | Y        | 최근접 역, 도보 시간                                                                  | FR-606, FR-207                     |
| location              | embedding                                                 | VECTOR(1024)                                | \-        | Y        | 이름·설명·태그·촬영 작품 장르의 bge-m3 임베딩                                         | FR-617, FR-309                     |
| shooting              | work_id, location_id, source_id                           | INT, INT, VARCHAR(10)                       | PK·FK     | N        | 작품–촬영지 관계(출처별 1행)                                                          | FR-602, FR-106                     |
| shooting              | raw, base_date                                            | JSONB, DATE                                 | \-        | N        | 원본 레코드(값 보존), 자료 기준일                                                     | FR-611                             |
| station               | id, name, line, lat, lon, gu                              | VARCHAR(10), TEXT 등                        | PK        | N        | 부산 도시철도역(DATA-08)                                                              | FR-202, FR-606                     |
| station_time          | from_id, to_id, minutes                                   | VARCHAR(10), REAL                           | PK·FK     | N        | 모든 역 쌍의 최소 소요시간(역간 소요시간으로 배치에서 미리 계산)                      | FR-313, BR-12                      |
| photo                 | id, location_id, url                                      | SERIAL, INT, TEXT                           | PK·FK     | N        | 장소 사진 주소(파일은 저장하지 않음)                                                  | FR-207                             |
| photo                 | kogl_type, title, source_id                               | SMALLINT, TEXT, VARCHAR(10)                 | FK        | N        | 공공누리 유형(CHECK = 1), 원 제목, 출처                                               | BR-03                              |
| course                | id, theme, theme_ref, title                               | SERIAL, VARCHAR(8), TEXT                    | PK        | N        | 추천 코스(work·actor·area 테마)                                                       | FR-301, FR-614                     |
| course                | start_label, start_lat, start_lon, total_min, total_m     | TEXT, DOUBLE, INT                           | \-        | N        | 출발지, 총 소요 시간·거리                                                             | FR-302                             |
| course                | status, approved_by, approved_at                          | VARCHAR(10), TEXT, TIMESTAMPTZ              | \-        | Y        | draft·approved(승인된 것만 공개)                                                      | FR-614                             |
| course_stop           | course_id, ord, location_id                               | INT, SMALLINT, INT                          | PK·FK     | N        | 방문 순서                                                                             | FR-302                             |
| course_stop           | dwell_min, leg_mode, leg_min, leg_line                    | SMALLINT, VARCHAR(4), SMALLINT, VARCHAR(10) | \-        | Y        | 체류(기본 20분), 다음 장소까지 이동 수단·시간·노선                                    | FR-313, BR-13                      |
| review_item           | id, kind, target_type, target_id                          | BIGSERIAL, VARCHAR(5), VARCHAR(8), INT      | PK        | N        | 검수 항목(tag·match)과 대상(location·work)                                            | FR-608                             |
| review_item           | proposal, proposer, model, score                          | JSONB, VARCHAR(4), TEXT, REAL               | \-        | Y        | 제안 내용, 제안 주체(rule·ai), 사용 모델, 점수                                        | FR-608, AI-REQ-13                  |
| review_item           | status, handled_by, handled_at, created_at                | VARCHAR(8), TEXT, TIMESTAMPTZ               | \-        | Y        | pending·approved·rejected, 처리자·일시                                                | FR-609, BR-04                      |
| dict_entry            | id, kind, surface, canonical_id                           | BIGSERIAL, VARCHAR(8), TEXT                 | PK        | N        | 사전 표면형(작품·인물·구·군·역·태그)과 표준 ID                                        | FR-403                             |
| dict_entry            | embedding                                                 | VECTOR(1024)                                | \-        | Y        | 표면형 임베딩(퍼지 매칭 실패 시 의미 검색)                                            | FR-617                             |
| sync_run              | id, trigger, status, requested_by                         | BIGSERIAL, VARCHAR(8), VARCHAR(10), TEXT    | PK        | N        | schedule·manual, requested·running·published·rejected·failed                          | FR-613·616                         |
| sync_run              | counts, prev_counts, failures, started_at, finished_at    | JSONB, TIMESTAMPTZ                          | \-        | Y        | 단계별 건수·비율, 직전 건수, 실패 목록(URL·키 제외), 최근 10회 보관                   | FR-612·613                         |
| ai_cache              | key                                                       | CHAR(64)                                    | PK        | N        | SHA-256(작업 + 프롬프트 버전 + 마스킹한 입력 + 근거 해시)                             | AI-REQ-15                          |
| ai_cache              | task, response, created_at, expires_at                    | VARCHAR(20), JSONB, TIMESTAMPTZ             | \-        | N        | 검증을 통과한 응답만, 24시간 뒤 삭제. 근거에 NO_STORE 데이터가 있으면 저장하지 않음   | AI-REQ-15, NFR-007                 |
| usage_counter         | day, key, count                                           | DATE, VARCHAR(40), INT                      | PK        | N        | 공급자·모델별, 데이터셋별 하루 호출 수(원자적 증가)                                   | NFR-005, NFR-018                   |
| 서버 메모리           | SessionStore                                              | dict(TTL 30분)                              | \-        | \-       | 세션 ID별 최근 3턴 조건, 재시작 시 삭제                                               | FR-408                             |
| 브라우저 localStorage | cl.stamps, cl.badges, cl.courses, cl.favorites, cl.notice | JSON                                        | \-        | \-       | 스탬프·배지 토큰, 저장 코스(최대 10), 즐겨찾기, 안내 확인 버전                        | FR-306, FR-504·508, FR-701, FR-801 |
| 토큰 형식             | stamp, badge                                              | JWT(HS256)                                  | \-        | \-       | stamp {typ, loc, iat, kid}, badge {typ, course_key, iat, kid}. 좌표 없음, 만료 없음   | FR-504, NFR-011                    |
| 로그 파일             | logs/\*.jsonl                                             | JSON Lines                                  | \-        | \-       | 요청 ID, 경로 템플릿, 상태, 응답 시간, AI 공급자·호출 수, 마스킹한 질의. 7일 회전     | NFR-005                            |

# 6. API 설계

| **API ID** | **Method** | **Endpoint**              | **목적**                 | **Request**                                             | **Response**                                                                            | **관련 요구사항**               |
|------------|------------|---------------------------|--------------------------|---------------------------------------------------------|-----------------------------------------------------------------------------------------|---------------------------------|
| API-001    | GET        | /api/works                | 작품 목록·검색·정렬      | q, genre, sort(year·locations), page                    | {items\[20\], total}                                                                    | FR-101·102                      |
| API-002    | GET        | /api/works/{id}           | 작품 상세                | \-                                                      | {work, people\[≤5\], plot, images, vod, locations\[\], related\[≤5\], source_ids}       | FR-103~106, FR-210, FR-802      |
| API-003    | GET        | /api/works/{id}/rating    | KOBIS 관람등급 실시간    | \-                                                      | {rating 또는 null, source_ids}                                                          | FR-107                          |
| API-004    | POST       | /api/works/{id}/intro     | AI 작품 소개             | {spoiler: none·partial}                                 | {status, sentences\[\], degraded, fallback, source_ids}                                 | FR-108~111, FR-707              |
| API-005    | POST       | /api/locations/search     | 근접·필터 검색           | {base: {lat, lon}·{station_id}·{gu}, radius_m, filters} | {items\[{id, name, lat, lon, distance_m, works\[≤3\], station}\]}                       | FR-201~206, FR-210              |
| API-006    | GET        | /api/locations/{id}       | 촬영지 상세              | \-                                                      | {location, photo, tags, station, walk_min, works\[\], caution, certifiable, source_ids} | FR-207~209, FR-506              |
| API-007    | GET        | /api/meta                 | 선택 목록                | \-                                                      | {districts\[16\], stations\[\], genres\[\], year_range}                                 | FR-202, FR-205, FR-410          |
| API-008    | GET        | /api/stats/districts      | 구·군별 통계(Should)     | \-                                                      | \[{gu, locations, works}\]                                                              | FR-803                          |
| API-009    | GET        | /api/courses              | 추천 코스 목록           | theme                                                   | \[{id, title, stops, total_min, total_m}\]                                              | FR-301                          |
| API-010    | GET        | /api/courses/{id}         | 추천 코스 상세           | \-                                                      | {course, stops\[\], legs\[\], total_min}                                                | FR-302                          |
| API-011    | POST       | /api/courses/plan         | 나만의 코스 경로         | {start, location_ids\[2~10\], fixed_order}              | {stops\[\], legs\[{mode, line, min}\], total_min, total_m}                              | FR-303~305, FR-313              |
| API-012    | POST       | /api/courses/ai           | AI 맞춤 코스             | {preference(≤200자) 또는 manual, start, budget_h(1~8)}  | {status, preference, route, reasons\[\], intro, masked}                                 | FR-307~312, FR-702              |
| API-013    | POST       | /api/query                | AI 대화형 탐색           | {text(≤200자)}                                          | {status, chips\[\], choices\[\], items\[≤20\], summary, relaxed\[\], masked, prefill}   | FR-401~409, FR-411·412, FR-702  |
| API-014    | POST       | /api/search               | 필터 패널 검색           | {conditions}                                            | {items\[≤20\], relaxed\[\]}                                                             | FR-405·406, FR-410              |
| API-015    | DELETE     | /api/query/session        | 새 대화(맥락 삭제)       | \-                                                      | 204                                                                                     | FR-408                          |
| API-016    | POST       | /api/stamps               | 방문 인증                | {location_id, lat, lon, accuracy_m, held\[\]}           | {ok, token 또는 reason, distance_m}                                                     | FR-501~506                      |
| API-017    | POST       | /api/stamps/verify        | 토큰 서명 확인           | {tokens\[\]}                                            | {valid\[{location, work, iat}\], invalid_count}                                         | FR-507                          |
| API-018    | POST       | /api/badges               | 완주 배지                | {course: {id}·{location_ids\[\]}, stamps\[\]}           | {ok, token 또는 missing\[\]}                                                            | FR-508                          |
| API-019    | GET        | /api/sources              | 출처 대장·라이선스       | \-                                                      | {sources\[\], licenses\[\], kobis_notice}                                               | FR-705                          |
| API-020    | POST       | /api/admin/session        | 관리자 로그인            | {password}                                              | 204 + 쿠키, 401, 423                                                                    | FR-615                          |
| API-021    | POST·GET   | /api/admin/sync           | 동기화 요청·리포트       | \- / limit=10                                           | 202 {run_id} / \[{run, counts, guard, failures}\], usage                                | FR-601, FR-612·613·616, NFR-005 |
| API-022    | GET·PATCH  | /api/admin/reviews        | 검수 큐 조회·처리        | status / {id, action, edit}                             | items / item                                                                            | FR-608·609                      |
| API-023    | PATCH      | /api/admin/locations/{id} | 촬영지 속성 편집         | {caution, safety_note, cert_radius_m, cert_excluded}    | location                                                                                | FR-610                          |
| API-024    | POST·PATCH | /api/admin/courses        | 추천 코스 후보 생성·승인 | {theme, ref} / {id, stops, status}                      | course                                                                                  | FR-614                          |
| API-025    | GET        | /api/health               | 상태 확인                | \-                                                      | {db, ai_breakers, gemini_usage}                                                         | NFR-002, NFR-005, NFR-020       |

- 모든 응답은 JSON(UTF-8)이고 오류는 {error: {code: ERR-xxx, message, retry_after}} 형식입니다(8장). 상세 스키마는 FastAPI가 만드는 OpenAPI 문서로 관리하고 프런트엔드 타입을 여기서 생성합니다.

- 정밀 위치가 들어가는 요청(API-005·016)은 POST 본문으로만 받습니다. URL과 접근 로그에 좌표가 남지 않습니다(NFR-003).

- 모든 요청에 X-Session-Id(탭마다 만든 임의 UUID)를 붙입니다. AI를 쓰는 요청(API-004·012·013)은 X-Notice-Version(확인한 이용 안내 버전)이 없으면 403입니다(FR-701). 관리자 API(API-020~024)는 API-020이 발급한 쿠키(HttpOnly·Secure·SameSite=Strict, 2시간)로 인증합니다.

- 응답의 source_ids는 표현 계층이 출처 카드(제공기관·데이터명·기준일·원문 링크)로 바꾸고, AI 문장에는 ai_generated: true를 붙입니다(ADR-014, FR-707).

# 7. AI / LLM / VLM 설계

## 7.1 AI 파이프라인

AI는 자연어를 조건으로 바꾸고 시스템이 찾은 결과를 설명하는 데만 씁니다(SRS 8.1). 요청 1건의 외부 AI 호출은 많아야 2회이고, 나머지 단계는 팀이 구현하는 결정론적 로직입니다. 근거가 없으면 생성 단계로 가지 않고(근거 게이트), 생성한 문장은 근거와 대조해 어긋난 문장을 지웁니다. 지도·인증·필터 검색은 이 파이프라인을 쓰지 않습니다.

<img src="media/image14.png" style="width:6.69291in;height:4.61811in" />

그림 14. AI 파이프라인 — 주황: LLM 호출, 초록: 팀 구현 로직, 흰색: 데이터 접근, 빨간 점선: 강등 경로

관련 요구사항: AI-REQ-01~09, FR-109~111, FR-308~312, FR-402~411, NFR-002·006

## 7.2 모델 및 인터페이스

| **AI 요소**              | **모델/서비스**                           | **역할**                                  | **입력/출력**                                   | **교체 가능성/추상화**                             | **관련 요구사항**        |
|--------------------------|-------------------------------------------|-------------------------------------------|-------------------------------------------------|----------------------------------------------------|--------------------------|
| 조건 추출(F4)            | Gemini Flash 계열(무료) → Ollama qwen3:8b | 질의를 검색 조건으로                      | 마스킹한 질의 + 허용 값 목록 → Conditions JSON  | LLMClient(task=extract_query). 실패 시 필터 패널   | FR-402·409, AI-REQ-04·09 |
| 결과 요약(F4)            | 위와 같음                                 | 상위 10건만 근거로 3문장 이내 요약        | 근거 묶음 → {sentences\[{text, entities\[\]}\]} | LLMClient(summarize_results). 실패 시 결과만       | FR-407, AI-REQ-01·06     |
| 취향 구조화(F3)          | 위와 같음                                 | 취향 문장을 취향·제약으로                 | 마스킹한 문장 → Preference JSON                 | LLMClient(structure_preference). 실패 시 직접 선택 | FR-308, AI-REQ-04        |
| 코스 소개(F3)            | 위와 같음                                 | 확정 코스의 선정 이유·소개                | 코스 데이터 → {reasons\[\], intro}              | LLMClient(course_intro). 실패 시 템플릿 문장       | FR-311                   |
| 작품 소개(F1)            | 위와 같음                                 | 부산 촬영지 관점 소개(300~500자)          | 근거 묶음 → {sentences\[{text, entities\[\]}\]} | LLMClient(work_intro). 실패 시 원문 강등           | FR-109~111               |
| 태그·매칭 제안(C1)       | Ollama qwen3:8b 우선 → Gemini             | 규칙 미분류 촬영지 태그, 애매한 매칭 판정 | 장소·작품 정보 → {tags\[\]·verdict, reason}     | LLMClient(suggest_tags·judge_match), 배치 전용     | FR-608, AI-REQ-13        |
| 임베딩                   | Ollama bge-m3(1024차원)                   | 사전 의미 검색, 취향 유사도               | 텍스트 → 벡터                                   | Embedder(OllamaEmbedder), 모델명은 설정값          | FR-617, FR-309, FR-403   |
| (Could) 포스터 글자 인식 | Ollama qwen3-vl:8b                        | 포스터 글자만 읽기(사진 미저장)           | 이미지 → 글자                                   | LLMProvider에 이미지 입력 추가(확장 지점)          | FR-901                   |

모델 이름, 작업별 공급자 순서, temperature(0~0.3), 제한 시간, 프롬프트·스키마 버전은 config/ai.yaml 한 파일에 둡니다. Gemini 무료 모델명과 한도는 착수 때 AI Studio에서 다시 확인합니다(TBD-05). 바꿀 때마다 평가셋(AI-REQ-10~13)을 다시 돌려 결과를 기록합니다(AI-REQ-14).

## 7.3 Prompt 설계

- **System Prompt 목적**: 작업마다 역할을 하나로 고정한 프롬프트 7개(prompts/\<작업\>.v\<번호\>.md)를 씁니다. 공통 지시는 '주어진 근거 묶음 안의 정보만 쓴다, 근거에 없으면 쓰지 않는다, 출력은 지정한 JSON 스키마만, SQL·코드·명령을 만들지 않는다'입니다. 사용자 입력은 \<user_input\> 구분자 안에 넣고 지시가 아닌 데이터로 다루게 합니다(AI-REQ-09).

- **검색 대상 데이터/Chunk 전략**: 이 서비스의 근거는 문서 조각이 아니라 지식베이스의 구조화 레코드입니다. 근거 묶음은 레코드 단위 JSON(작품 정보, 촬영지 행, 코스 구간)이고 각 항목에 ID와 출처 ID를 붙입니다. 임베딩은 사전 표면형과 촬영지 설명에만 씁니다.

- **Top-k 또는 Retrieval 기준**: F4 요약은 검색 결과 상위 10건(FR-407), F1은 그 작품의 촬영지 전체(최대 20곳), F3는 확정된 코스의 3~8곳입니다. 사전 대조는 트라이그램 유사도 상위 3개를 쓰고, 0.35 미만이면 임베딩 코사인 유사도 0.75 이상인 후보로 보완합니다(초기값, 평가셋으로 확정).

- **출처 표시 방식**: AI 응답에는 출처 문구를 쓰게 하지 않습니다. 서버가 근거 묶음의 출처 ID를 출처 대장으로 바꿔 출처 카드를 붙이고, AI 문장에는 'AI 생성' 표시를 붙입니다(ADR-014, AI-REQ-08).

- **Hallucination 완화**: 근거 게이트, 근거 밖 지식 사용 금지 지시, 문장별 인명·작품명·장소명·연도·시간 수치 대조(COMP-09), 결말·반전 표현 검사, JSON 스키마와 허용 값 검증, 낮은 temperature, 숫자(시간·거리)는 시스템 계산값만 근거 묶음에 넣음, 원문(줄거리·결과 목록)을 함께 표시.

관련 요구사항: AI-REQ-01·03~09·14, FR-109~111, FR-311, FR-402·407

## 7.4 AI 실패/예외 처리

| **상황**                                 | **처리 전략**                                                                                                                                                    | **사용자 메시지/로그**                                                 | **관련 요구사항**                |
|------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|----------------------------------|
| API 오류·시간 초과(10초)·429             | 작업별 대체 체인으로 다음 공급자. 429는 Retry-After가 2초 이하면 같은 공급자에 1번 다시. 연속 5회 실패하면 차단기를 60초 엶. 남은 마감 시간이 모자라면 바로 강등 | "AI 대신 기본 결과를 보여 드립니다" / provider, error_code, latency_ms | AI-REQ-02, NFR-002               |
| 스키마 위반·허용 값 밖                   | 같은 공급자에 1회 다시, 그다음 공급자, 모두 실패하면 강등                                                                                                        | 강등 응답 / error_code=AI_SCHEMA                                       | AI-REQ-04                        |
| 근거 부족(검색 0건, 근거 묶음 비어 있음) | 생성하지 않음(근거 게이트). F4는 조건 완화 후에도 0건이면 '찾지 못함'과 필터 패널                                                                                | "조건에 맞는 촬영지를 찾지 못했습니다" / status=NOT_FOUND              | FR-405·407, AI-REQ-01            |
| 근거 대조 실패·결말 표현                 | 해당 문장 삭제. F1은 남은 문장이 2개 미만이면 원문 줄거리·촬영지로 강등, F4는 요약 없이 결과만, F3는 템플릿 선정 이유                                            | 강등 표시 / dropped_count                                              | FR-110·111, FR-311, AI-REQ-06·07 |
| 범위 밖 질의·지시 주입 시도              | 검색하지 않고 서비스 범위 안내. 사용자 입력은 데이터로만 다루고, 출력은 조건 스키마라 주입이 성공해도 조건 값 외에는 영향 없음                                   | "부산 촬영지·작품에 관한 질문에 답할 수 있어요" / status=OUT_OF_SCOPE  | FR-409, AI-REQ-09                |
| 개인정보가 든 입력                       | 마스킹한 뒤 진행하고 알림                                                                                                                                        | "개인정보로 보이는 내용을 가렸습니다" / 마스킹 종류만 기록             | FR-702, AI-REQ-03                |
| Gemini 일일 호출 70%·100%                | 70%면 관리자 화면 경고와 Ollama 우선, 100%면 Gemini를 건너뜀                                                                                                     | 관리자 리포트 / usage_counter                                          | NFR-005, NFR-018                 |
| 세션당 AI 요청 분당 5회 초과             | 429와 Retry-After(ERR-011)                                                                                                                                       | "잠시 후 다시 시도해 주세요"                                           | AI-REQ-15                        |

# 8. 예외 처리 및 로깅

| **오류 ID** | **오류 상황**                                                                  | **시스템 동작**                                                  | **로그/모니터링**                             | **관련 요구사항**                |
|-------------|--------------------------------------------------------------------------------|------------------------------------------------------------------|-----------------------------------------------|----------------------------------|
| ERR-001     | 입력 형식·길이·범위 오류(200자 초과, 부산 밖 좌표, 장소 2~10곳 밖, 반경 값 밖) | 422, 필드별 안내                                                 | error_code, 경로(입력 값은 남기지 않음)       | FR-303, FR-307, FR-401 / NFR-010 |
| ERR-002     | 이용 안내 미확인(X-Notice-Version 없음)                                        | 403, 화면은 안내 모달                                            | error_code                                    | FR-701                           |
| ERR-003     | 외부 AI 장애·한도(7.4)                                                         | 대체 체인 → 강등 응답(200, degraded=true)                        | provider, error_code, latency_ms, 차단기 상태 | AI-REQ-02 / NFR-002              |
| ERR-004     | AI 출력 스키마 위반                                                            | 1회 재요청 → 다음 공급자 → 강등                                  | error_code=AI_SCHEMA                          | AI-REQ-04                        |
| ERR-005     | 근거 대조 뒤 문장 부족                                                         | F1 원문 강등, F4 요약 생략, F3 템플릿 문장                       | dropped_count                                 | FR-110, FR-311, FR-407           |
| ERR-006     | KOBIS 3초 초과·오류                                                            | rating=null, 화면은 등급 없이 표시                               | provider=kobis, latency_ms                    | FR-107                           |
| ERR-007     | KMDb 실시간 조회 실패(ID_ONLY일 때)                                            | 저장된 기본 항목만, 나머지는 '정보 없음'                         | provider=kmdb, error_code                     | FR-103                           |
| ERR-008     | 지오펜스 실패(정확도 50m 초과, 반경 밖)                                        | 200 {ok: false, reason, distance_m}                              | 판정 결과만(위치 미기록)                      | FR-502·503                       |
| ERR-009     | 인증 제외·좌표 없는 촬영지 인증 요청                                           | 409와 제외 이유                                                  | error_code                                    | FR-506, BR-06                    |
| ERR-010     | 토큰 서명 불일치·변조                                                          | 확인 결과에서 제외하고 개수만 알림(invalid_count)                | 거부 건수                                     | FR-507, NFR-011                  |
| ERR-011     | 속도 제한 초과                                                                 | 429 + Retry-After                                                | 경로, 시각                                    | AI-REQ-15, NFR-018               |
| ERR-012     | 관리자 인증 실패·잠금                                                          | 401, 5회 연속 실패하면 423으로 10분 잠금                         | 실패 횟수(비밀번호는 남기지 않음)             | FR-615 / NFR-009                 |
| ERR-013     | 외부 데이터 API 실패·응답 형식 변경(배치)                                      | 3회 재시도 후 그 데이터셋 중단, 직전 데이터 유지                 | sync_run.failures(URL·키 제외)                | FR-601, FR-613, IF-01            |
| ERR-014     | 적재 건수 가드 위반                                                            | 반영하지 않음, 관리자 화면 경고                                  | fetched, prev_counts, 사유                    | FR-612, BR-14                    |
| ERR-015     | DB 연결 실패                                                                   | 503\. 화면은 브라우저에 저장된 스탬프북·저장 코스를 계속 보여 줌 | 헬스 체크(API-025)                            | NFR-020                          |
| ERR-016     | 처리하지 못한 서버 오류                                                        | 500과 요청 ID                                                    | 스택 추적(정제 후)                            | NFR-005                          |

**로그 정책**: 요청 로그(logs/\*.jsonl)에는 요청 ID, 경로 템플릿, 상태, 응답 시간, AI 공급자·호출 수, 오류 코드를 남기고, F3·F4 요청만 마스킹한 입력을 함께 남깁니다. 위치 좌표, 입력 원문, 토큰, 카카오·KOBIS 응답, 인증키, IP는 남기지 않습니다. 모든 레코드는 PrivacyGuard.scrub()을 거치고 7일 뒤 지웁니다(NFR-003·005). 운영 지표는 관리자 리포트(API-021)와 헬스 체크(API-025)로 확인합니다.

# 9. 보안 및 개인정보 설계

- **인증/권한**: 일반 사용자는 로그인하지 않습니다. 관리 기능(API-020~024, UI-10~12)은 서버 환경변수의 관리자 비밀번호 해시(argon2)와 비교해 발급한 쿠키 세션으로만 씁니다. 5회 연속 실패하면 10분 동안 시도를 막고, 접속은 HTTPS로만 받습니다(FR-615, NFR-012).

- **API Key/Secret 관리**: Gemini·KMDb·KOBIS·공공데이터포털·주소·TourAPI 키, 관리자 비밀번호 해시, 토큰 서명 키는 서버 .env와 GitHub Secrets에만 둡니다. 저장소에는 .env.example만 올리고 pre-commit gitleaks와 CI로 검사합니다. 브라우저에는 카카오 JavaScript 키만 두고 등록 도메인으로 제한합니다. 노출되면 즉시 폐기·재발급하고, 토큰 서명 키는 kid로 교체할 수 있게 합니다(NFR-009).

- **개인정보 저장 최소화**: 회원 정보, 위치 좌표, 입력 원문, 스탬프 기록을 서버에 저장하지 않습니다. 위치는 POST 본문으로 받아 요청 처리 중에만 쓰고, 프롬프트에는 좌표를 넣지 않습니다(출발지가 현재 위치면 '현재 위치'라는 표지만). 스탬프·코스·즐겨찾기는 브라우저에만 둡니다(NFR-003, AI-REQ-03).

- **입력/출력 검증**: Pydantic으로 길이(200자)·형식·범위(부산 좌표, 반경 값, 장소 수)를 검사하고, DB 질의는 바인딩 매개변수만 씁니다. AI 출력은 JSON 스키마·허용 값·근거 대조를 통과한 것만 쓰고, 화면은 React 기본 이스케이프와 CSP로 스크립트 삽입을 막습니다(NFR-010, AI-REQ-04·05).

- **로그에 민감정보를 남기지 않음**: 질의는 마스킹본만, 접근 로그는 경로와 상태만 남기고 쿼리 문자열과 본문은 남기지 않습니다. 가짜 개인정보 50건과 위치 요청 100회 뒤 로그·DB 감사에서 원본 0건을 확인합니다(NFR-003·005).

## 관련 요구사항 매핑

| **보안/개인정보 설계 요소** | **관련 요구사항**                  |
|-----------------------------|------------------------------------|
| 인증/권한                   | FR-615, NFR-012                    |
| API Key/Secret 관리         | NFR-009                            |
| 개인정보 저장 최소화        | NFR-003 / AI-REQ-03, BR-10         |
| 입력/출력 검증              | NFR-010, NFR-011 / AI-REQ-04·05·09 |
| 민감정보 로그 방지          | NFR-003, NFR-005 / AI-REQ-03       |

# 10. 배포 및 운영 설계

## 10.1 Deployment Diagram

<img src="media/image15.png" style="width:6.69291in;height:4.28346in" />

그림 15. 배치 다이어그램(시연·운영 환경과 개발 환경)

관련 요구사항: NFR-002·003·009·012·017·020

- **시연·운영**: 팀 서버에서 Docker Compose로 컨테이너 6개(tunnel, web, api, batch, db, ollama)를 띄우고 Cloudflare 터널로 HTTPS 주소를 엽니다. 터널은 서버에서 바깥으로만 연결하므로 공개 포트를 열지 않습니다. 브라우저 위치 기능에는 HTTPS가 필요하고 카카오 JavaScript 키는 이 주소의 도메인을 등록합니다.

- **api 컨테이너는 워커 1개**로 띄웁니다. 대화 맥락과 로그인 실패 횟수를 메모리에 두기 때문입니다(ADR-013). 동시 10명 부하(NFR-001·006)는 비동기 I/O로 처리하며, 부하 시험 결과가 목표에 못 미치면 맥락 저장을 DB로 옮기고 워커를 늘립니다.

- **개발**: 팀원 PC는 GPU가 없으므로 web·api·db만 띄우고 AI_PROVIDER=gemini로 개발합니다. 지식베이스와 임베딩은 GitHub Release의 seed.sql.gz를 적재해 쓰고, 배치와 임베딩 생성은 팀 서버에서만 실행합니다.

- **운영 점검**: 컨테이너 자동 재시작, 매일 pg_dump 백업(30분 안에 복원, NFR-020), 시연 전 헬스 체크(API-025)와 백업 시연 영상을 준비합니다.

## 10.2 CI/CD

- **Repository/Branch 전략**: 저장소 하나(frontend, backend, batch, eval, docs, infra). GitHub Flow로 main은 보호 브랜치이고 작업 브랜치는 feature/이슈번호-요약, fix/…, docs/…입니다(계획서 17.2~17.3).

- **Pull Request/Review 규칙**: PR 템플릿(변경 내용, 관련 요구사항 ID, 테스트 방법, 의존성 라이선스, AI 도움 여부)을 쓰고, 리뷰어 1명 승인과 CI 통과 뒤 squash 병합합니다. 프롬프트(prompts/)와 저장 정책(config/providers.yaml) 변경은 평가셋 결과를 PR에 첨부합니다.

- **자동 Build/Test**: GitHub Actions가 PR마다 backend(ruff, pytest·커버리지), frontend(eslint, tsc, vitest), import 규칙 검사, 저장 정책 검사(NO_STORE 열 없음), gitleaks, Docker 빌드를 돌립니다. 외부 API는 저장 가능한 실제 응답 사본과 저장 금지 데이터의 가짜 응답으로 바꿔 무료 한도를 쓰지 않습니다. Playwright E2E는 main 병합 때 돌립니다.

- **배포 환경**: 태그(v0.1-midterm, v1.0)를 팀 서버에서 받아 docker compose up -d로 띄웁니다. .env는 서버에만 있습니다.

관련 요구사항: NFR-007·009·016·017 / 계획서 17장

# 11. 디자인 패턴 및 주요 설계 원칙

디자인 패턴은 10주차 강의 범위이므로 v0.1에서는 적용 위치와 이유만 정하고, 강의 뒤 v0.2에서 구조를 점검합니다.

| **패턴/원칙**                    | **적용 위치**                   | **적용 이유**                                           | **관련 클래스/컴포넌트**                                  | **관련 요구사항**     |
|----------------------------------|---------------------------------|---------------------------------------------------------|-----------------------------------------------------------|-----------------------|
| 계층형(Layered)                  | API 서버 전체                   | 관심사 분리, 계층별 시험, 외부 변경 영향 격리           | COMP-02 → 03~07·14 → 09·10·15 → 08·11·12                  | NFR-015·016, ADR-002  |
| 파이프-필터                      | F4 파이프라인, 동기화 배치      | 단계별 시험·교체, 근거 게이트로 생성 차단               | QueryPipeline·QueryStep, SyncJob·IngestStep               | AI-REQ-01·04, ADR-003 |
| Repository                       | 데이터 접근                     | SQL을 저장소에 모아 서비스는 도메인 객체만 다룸         | WorkRepository 등 10종                                    | NFR-016               |
| Adapter                          | 외부 데이터·AI 연동             | 외부 응답 형식·인증·오류를 한 곳에서 처리               | BaseApiClient 하위 클래스, GeminiProvider, OllamaProvider | NFR-015, ADR-004      |
| Strategy                         | AI 공급자, 근거 정책, 경로 계산 | 같은 인터페이스로 구현을 설정·상황에 따라 교체          | LLMProvider, EvidencePolicy, RoutePlanner                 | NFR-015, AI-REQ-07    |
| Chain of Responsibility          | AI 대체 체인                    | 앞 공급자가 실패하면 다음 공급자가 처리                 | ProviderChain                                             | AI-REQ-02, NFR-002    |
| Circuit Breaker                  | 공급자별 연속 실패              | 장애 공급자를 잠시 건너뛰어 응답 시간 보호              | CircuitBreaker                                            | AI-REQ-02, NFR-006    |
| Template Method                  | 외부 데이터 수집                | 페이지 반복·재시도·검사는 공통, 데이터별 parse()만 다름 | BaseApiClient.fetch_all(), parse()                        | FR-601, NFR-018       |
| 의존성 주입(DI)                  | 서비스·어댑터 연결              | 시험에서 어댑터를 가짜로 교체                           | FastAPI Depends, 서비스 생성자                            | NFR-016               |
| 높은 응집·낮은 결합, 단일 진입점 | 컴포넌트 분할, 외부 접근        | 기능별 응집(3.3), 외부 AI는 LLMClient 하나로만 호출     | COMP-03~08, COMP-11                                       | AI-REQ-03, 강의 6주차 |

# 12. 요구사항-설계 추적표

SRS v0.1의 요구사항 120개를 유스케이스, 컴포넌트, 클래스·테이블, API, 시퀀스, 테스트 케이스와 연결했습니다. 유스케이스·설계 요소가 같은 연속 ID는 한 행으로 묶었고(예: FR-101~102), Test Case ID는 SRS 10장 규칙을 따릅니다. '-'는 해당 설계 요소가 없다는 뜻입니다(예: 화면만으로 처리하는 요구는 API가 없음). 설계가 바뀌면 스프린트마다 SRS 10장과 함께 갱신합니다.

| **요구사항 ID**  | **Use Case**      | **컴포넌트**           | **Class/DB**                                                                             | **API**         | **Sequence** | **Test Case** | **상태** |
|------------------|-------------------|------------------------|------------------------------------------------------------------------------------------|-----------------|--------------|---------------|----------|
| FR-101~102       | UC-01             | COMP-01·03·12          | ArchiveService.list_works, WorkRepository.page / work                                    | API-001         | \-           | TC-101~102    | Draft    |
| FR-103           | UC-01             | COMP-01·03·11          | ArchiveService.get_work, MovieInfoProvider / work, work_person                           | API-002         | \-           | TC-103        | Draft    |
| FR-104~105       | UC-01             | COMP-01·03·11          | ArchiveService.get_work / work.kmdb                                                      | API-002         | \-           | TC-104~105    | Draft    |
| FR-106           | UC-01             | COMP-01·03·11          | ArchiveService.get_work / shooting                                                       | API-002         | \-           | TC-106        | Draft    |
| FR-107           | UC-01             | COMP-03·11             | ArchiveService.get_rating, RatingProvider / work.kobis_movie_cd                          | API-003         | \-           | TC-107        | Draft    |
| FR-108           | UC-02             | COMP-01·03             | ArchiveService.get_intro, EvidencePolicy                                                 | API-004         | SD-01        | TC-108        | Draft    |
| FR-109           | UC-02             | COMP-03·08             | NoSpoilerEvidence, PartialSpoilerEvidence, ProviderChain                                 | API-004         | SD-01        | TC-109        | Draft    |
| FR-110~111       | UC-02             | COMP-03·09             | GroundingVerifier, PhraseFilter                                                          | API-004         | SD-01        | TC-110~111    | Draft    |
| FR-201~202       | UC-03             | COMP-01·04·12          | GeoProbe, MapService.search / station                                                    | API-005·007     | \-           | TC-201~202    | Draft    |
| FR-203           | UC-03             | COMP-01·04·12          | LocationRepository.within_radius / location                                              | API-005         | \-           | TC-203        | Draft    |
| FR-204           | UC-03             | COMP-01·04·12          | MapView                                                                                  | \-              | \-           | TC-204        | Draft    |
| FR-205~206       | UC-03             | COMP-01·04·12          | MapService.search / location, shooting                                                   | API-005         | \-           | TC-205~206    | Draft    |
| FR-207           | UC-04             | COMP-01·04             | MapService.get_location / location, photo                                                | API-006         | \-           | TC-207        | Draft    |
| FR-208           | UC-03·04          | COMP-01                | MapView                                                                                  | API-006         | \-           | TC-208        | Draft    |
| FR-209           | UC-04             | COMP-01·04             | MapService.get_location / location.caution                                               | API-006         | \-           | TC-209        | Draft    |
| FR-210           | UC-01·03          | COMP-01·04·12          | LocationRepository / location.lat                                                        | API-002·005     | \-           | TC-210        | Draft    |
| FR-301           | UC-07             | COMP-01·05             | CourseService.list_recommended, CourseService.get_course / course, course_stop           | API-009·010     | \-           | TC-301        | Draft    |
| FR-302           | UC-07·09          | COMP-01·05             | CourseService.list_recommended, CourseService.get_course / course, course_stop           | API-009·010     | \-           | TC-302        | Draft    |
| FR-303           | UC-08             | COMP-01·05             | CourseService.plan_custom, NearestNeighbor2Opt                                           | API-011         | \-           | TC-303        | Draft    |
| FR-304           | UC-08·15          | COMP-01·05             | CourseService.plan_custom, NearestNeighbor2Opt                                           | API-011         | \-           | TC-304        | Draft    |
| FR-305 (Should)  | UC-08             | COMP-01·05             | CourseService.plan_custom, NearestNeighbor2Opt                                           | API-011         | \-           | TC-305        | Draft    |
| FR-306           | UC-08·09          | COMP-01·05             | CourseStore                                                                              | \-              | SD-03        | TC-306        | Draft    |
| FR-307           | UC-09             | COMP-01·10             | CoursePages, PrivacyGuard.mask                                                           | API-012         | SD-03        | TC-307        | Draft    |
| FR-308           | UC-09             | COMP-05·08             | CourseService.plan_ai, ProviderChain                                                     | API-012         | SD-03        | TC-308        | Draft    |
| FR-309           | UC-09             | COMP-05·12             | CandidateScorer / location.embedding                                                     | API-012         | SD-03        | TC-309        | Draft    |
| FR-310           | UC-09             | COMP-05                | BudgetFitter                                                                             | API-012         | SD-03        | TC-310        | Draft    |
| FR-311           | UC-09             | COMP-05·08·09          | CourseNarrator, GroundingVerifier                                                        | API-012         | SD-03        | TC-311        | Draft    |
| FR-312           | UC-09             | COMP-01·05             | CourseService.plan_from_preference                                                       | API-012         | SD-03        | TC-312        | Draft    |
| FR-313           | UC-15             | COMP-05                | TravelTimeEstimator / station_time                                                       | API-011·012     | SD-03        | TC-313        | Draft    |
| FR-401           | UC-05             | COMP-01·02             | AskPage, Schemas                                                                         | API-013         | SD-02        | TC-401        | Draft    |
| FR-402           | UC-05             | COMP-06·08             | ConditionExtractor, ProviderChain                                                        | API-013         | SD-02        | TC-402        | Draft    |
| FR-403           | UC-05             | COMP-06·12             | DictionaryResolver / dict_entry                                                          | API-013         | SD-02        | TC-403        | Draft    |
| FR-404           | UC-05             | COMP-06·12             | TemplateSearcher, SearchTemplates / location                                             | API-013·014     | SD-02        | TC-404        | Draft    |
| FR-405           | UC-05·06          | COMP-06·12             | ConditionRelaxer                                                                         | API-013·014     | SD-02        | TC-405        | Draft    |
| FR-406           | UC-05·06          | COMP-01·06·15          | QueryContext, MapView, SourceRegistry.cards                                              | API-013·014     | SD-02        | TC-406        | Draft    |
| FR-407           | UC-05             | COMP-06·08·09          | EvidenceGate, ResultSummarizer, GroundingCheck                                           | API-013         | SD-02        | TC-407        | Draft    |
| FR-408           | UC-05             | COMP-06                | ContextMerger, SessionStore                                                              | API-013·015     | SD-02        | TC-408        | Draft    |
| FR-409           | UC-05             | COMP-06·08             | ConditionExtractor                                                                       | API-013         | SD-02        | TC-409        | Draft    |
| FR-410           | UC-06             | COMP-01·06             | QueryService.search, FilterPanel                                                         | API-014         | \-           | TC-410        | Draft    |
| FR-411           | UC-05·06          | COMP-01·06             | QueryService.ask, FilterPanel                                                            | API-013·014     | SD-02        | TC-411        | Draft    |
| FR-412           | UC-05             | COMP-01·06             | QueryContext                                                                             | API-013         | SD-02        | TC-412        | Draft    |
| FR-501~503       | UC-10             | COMP-01·07             | StampService.certify, Geofence                                                           | API-016         | SD-04        | TC-501~503    | Draft    |
| FR-504~505       | UC-10             | COMP-01·07             | TokenSigner                                                                              | API-016         | SD-04        | TC-504~505    | Draft    |
| FR-506           | UC-10             | COMP-01·07             | StampService.certify / location.cert_excluded                                            | API-006·016     | SD-04        | TC-506        | Draft    |
| FR-507           | UC-12             | COMP-01·07             | StampService.verify, StampBook                                                           | API-017         | \-           | TC-507        | Draft    |
| FR-508           | UC-11             | COMP-01·07             | StampService.issue_badge, TokenSigner, StampBook                                         | API-018         | SD-04        | TC-508        | Draft    |
| FR-509           | UC-12             | COMP-01·07             | StampBook                                                                                | \-              | \-           | TC-509        | Draft    |
| FR-601           | UC-16             | COMP-13·11·12          | SyncJob, CollectStep, FilmLocationClient / sync_run                                      | API-021         | \-           | TC-601        | Draft    |
| FR-602           | UC-16             | COMP-13·11·12          | NormalizeMergeStep / shooting                                                            | \-              | \-           | TC-602        | Draft    |
| FR-603           | UC-16             | COMP-13·11·12          | MatchWorksStep, WorkMatcher, KmdbClient / work, review_item                              | \-              | \-           | TC-603        | Draft    |
| FR-604           | UC-16             | COMP-13·11·12          | LinkKobisStep / work.kobis_movie_cd                                                      | \-              | \-           | TC-604        | Draft    |
| FR-605           | UC-16             | COMP-13·11·12          | GeocodeStep, JusoGeocoder / location                                                     | \-              | \-           | TC-605        | Draft    |
| FR-606           | UC-16             | COMP-13·11·12          | NearestStationStep / location, station                                                   | \-              | \-           | TC-606        | Draft    |
| FR-607           | UC-16             | COMP-13·11·12          | TagRulesStep / location.tags                                                             | \-              | \-           | TC-607        | Draft    |
| FR-608           | UC-16             | COMP-13·08             | SuggestAIStep, ProviderChain / review_item                                               | API-022         | \-           | TC-608        | Draft    |
| FR-609           | UC-17             | COMP-14·02             | AdminService.decide / review_item                                                        | API-022         | \-           | TC-609        | Draft    |
| FR-610           | UC-17             | COMP-14·02             | AdminService.update_location / location                                                  | API-023         | \-           | TC-610        | Draft    |
| FR-611           | UC-16             | COMP-13·11·12          | RecordSourcesStep / source                                                               | \-              | \-           | TC-611        | Draft    |
| FR-612           | UC-16             | COMP-13·11·12          | CountGuardStep / sync_run                                                                | API-021         | \-           | TC-612        | Draft    |
| FR-613           | UC-16             | COMP-13·14·12          | SyncJob, AdminService.sync_report / sync_run                                             | API-021         | \-           | TC-613        | Draft    |
| FR-614           | UC-18             | COMP-14·05             | AdminService.draft_course, RoutePlanner / course                                         | API-024         | \-           | TC-614        | Draft    |
| FR-615           | UC-16·17·18       | COMP-02                | AdminAuth                                                                                | API-020         | \-           | TC-615        | Draft    |
| FR-616 (Should)  | UC-16             | COMP-13·11·12          | SyncScheduler                                                                            | API-021         | \-           | TC-616        | Draft    |
| FR-617           | UC-16             | COMP-13·08·12          | EmbedStep, OllamaEmbedder / dict_entry, location.embedding                               | \-              | \-           | TC-617        | Draft    |
| FR-701           | UC-13             | COMP-01·02             | NoticeGate, NoticeCheck                                                                  | API-004·012·013 | \-           | TC-701        | Draft    |
| FR-702           | UC-14             | COMP-10                | PrivacyGuard.mask                                                                        | API-012·013     | SD-02·03     | TC-702        | Draft    |
| FR-703           | UC-16             | COMP-11                | PolicyGuard, StoragePolicy / source.policy                                               | \-              | \-           | TC-703        | Draft    |
| FR-704           | UC-04·05          | COMP-02·15·01          | ResponseAssembler, SourceRegistry.cards / source                                         | API-002·006·013 | SD-01·02     | TC-704        | Draft    |
| FR-705           | UC-13             | COMP-15·01             | SourceRegistry.ledger, SourcesPage / source                                              | API-019         | \-           | TC-705        | Draft    |
| FR-706           | UC-03             | COMP-01                | MapView                                                                                  | \-              | \-           | TC-706        | Draft    |
| FR-707           | UC-02·05·09       | COMP-01·02·09          | AiLabel, ResponseAssembler                                                               | API-004·012·013 | SD-01~03     | TC-707        | Draft    |
| FR-801 (Should)  | UC-19             | COMP-01                | FavoriteStore                                                                            | \-              | \-           | TC-801        | Draft    |
| FR-802 (Should)  | UC-20             | COMP-03·04·12          | WorkRepository.similar                                                                   | API-002         | \-           | TC-802        | Draft    |
| FR-803 (Should)  | UC-20             | COMP-03·04·12          | MapService.district_stats                                                                | API-008         | \-           | TC-803        | Draft    |
| FR-901 (Could)   | \-                | COMP-08·10             | LLMProvider(확장 지점)                                                                   | \-              | \-           | TC-901        | Draft    |
| FR-902 (Could)   | \-                | COMP-01                | WorkPages(확장 지점)                                                                     | \-              | \-           | TC-902        | Draft    |
| FR-903 (Could)   | \-                | COMP-11·04             | BaseApiClient(확장 지점)                                                                 | \-              | \-           | TC-903        | Draft    |
| NFR-001          | UC-01·03·07       | COMP-02·04·12          | LocationRepository.within_radius, StationRepository / location, station_time             | API-005·010·011 | \-           | TC-N01        | Draft    |
| NFR-002          | UC-05·06·09       | COMP-08                | ProviderChain, CircuitBreaker                                                            | API-004·012·013 | SD-01~03     | TC-N02        | Draft    |
| NFR-003          | UC-03·10·14       | COMP-10·07             | GeoFix, PrivacyGuard.scrub                                                               | API-005·016     | SD-04        | TC-N03        | Draft    |
| NFR-004          | \-                | COMP-01                | MapView, WorkPages                                                                       | \-              | \-           | TC-N04        | Draft    |
| NFR-005          | \-                | COMP-02·08·12          | RequestLogger, UsageRepository / usage_counter                                           | API-021·025     | \-           | TC-N05        | Draft    |
| NFR-006          | UC-02·05·09       | COMP-08·12             | ProviderChain, AICacheRepository / ai_cache                                              | API-004·012·013 | SD-01~03     | TC-N06        | Draft    |
| NFR-007          | \-                | COMP-11, INFRA         | PolicyGuard / source.policy                                                              | \-              | \-           | TC-N07        | Draft    |
| NFR-008          | UC-13             | COMP-02·15·01          | ResponseAssembler, SourceRegistry                                                        | \-              | \-           | TC-N08        | Draft    |
| NFR-009          | \-                | INFRA                  | INFRA(.env·GitHub Secrets·gitleaks)                                                      | \-              | \-           | TC-N09        | Draft    |
| NFR-010          | UC-05             | COMP-02·06·12          | Schemas, SearchTemplates                                                                 | API-013·014     | SD-02        | TC-N10        | Draft    |
| NFR-011          | UC-10·11·12       | COMP-07                | TokenSigner                                                                              | API-016·017·018 | SD-04        | TC-N11        | Draft    |
| NFR-012          | \-                | INFRA                  | INFRA(HTTPS 터널·nginx)                                                                  | \-              | \-           | TC-N12        | Draft    |
| NFR-013          | UC-03·01·05·09·12 | COMP-01                | MapView, AskPage, CoursePages                                                            | \-              | \-           | TC-N13        | Draft    |
| NFR-014 (Should) | UC-03             | COMP-01·04             | MapView, GeoProbe                                                                        | API-005         | \-           | TC-N14        | Draft    |
| NFR-015          | \-                | COMP-08·11             | ProviderChain, MovieInfoProvider, PolicyGuard                                            | \-              | \-           | TC-N15        | Draft    |
| NFR-016          | \-                | COMP-05·07·09·10·11·13 | Geofence, NearestNeighbor2Opt, WorkMatcher, GroundingVerifier, PrivacyGuard, PolicyGuard | \-              | \-           | TC-N16        | Draft    |
| NFR-017          | \-                | INFRA                  | Docker Compose(10장)                                                                     | \-              | \-           | TC-N17        | Draft    |
| NFR-018          | \-                | COMP-11·08             | ProviderChain, BaseApiClient / usage_counter                                             | \-              | \-           | TC-N18        | Draft    |
| NFR-019 (Could)  | \-                | COMP-01                | WorkPages, MapView                                                                       | \-              | \-           | TC-N19        | Draft    |
| NFR-020 (Should) | \-                | INFRA                  | Docker Compose(10장) / pg_dump                                                           | API-025         | \-           | TC-N20        | Draft    |
| AI-REQ-01        | UC-02·05·09       | COMP-09                | GroundingVerifier.gate, EvidenceBundle                                                   | API-004·012·013 | SD-01~03     | TC-A01        | Draft    |
| AI-REQ-02        | UC-02·05·09       | COMP-08                | ProviderChain, CircuitBreaker                                                            | API-004·012·013 | SD-01~03     | TC-A02        | Draft    |
| AI-REQ-03        | UC-14             | COMP-10·08             | PrivacyGuard.mask                                                                        | API-012·013     | SD-02·03     | TC-A03        | Draft    |
| AI-REQ-04        | UC-05·09·16       | COMP-08                | SchemaValidator                                                                          | API-012·013     | SD-02·03     | TC-A04        | Draft    |
| AI-REQ-05        | UC-05             | COMP-06·12             | TemplateSearcher, SearchTemplates                                                        | API-013         | SD-02        | TC-A05        | Draft    |
| AI-REQ-06        | UC-02·05·09       | COMP-09                | GroundingVerifier.verify, EntityLexicon                                                  | API-004·012·013 | SD-01~03     | TC-A06        | Draft    |
| AI-REQ-07        | UC-02             | COMP-03·09             | NoSpoilerEvidence, PhraseFilter                                                          | API-004         | SD-01        | TC-A07        | Draft    |
| AI-REQ-08        | UC-02·05·09       | COMP-01·02·15          | ResponseAssembler, AiLabel                                                               | API-004·012·013 | SD-01~03     | TC-A08        | Draft    |
| AI-REQ-09        | UC-05             | COMP-06·08             | ConditionExtractor, PromptRegistry                                                       | API-013         | SD-02        | TC-A09        | Draft    |
| AI-REQ-10        | UC-05             | COMP-06                | 평가 스크립트(eval/)                                                                     | \-              | \-           | TC-A10        | Draft    |
| AI-REQ-11        | UC-09             | COMP-05                | 평가 스크립트(eval/)                                                                     | \-              | \-           | TC-A11        | Draft    |
| AI-REQ-12        | UC-02             | COMP-03·09             | 평가 스크립트(eval/)                                                                     | \-              | \-           | TC-A12        | Draft    |
| AI-REQ-13        | UC-16·17          | COMP-13·14             | 평가 스크립트(eval/)                                                                     | \-              | \-           | TC-A13        | Draft    |
| AI-REQ-14        | \-                | COMP-08                | PromptRegistry                                                                           | \-              | \-           | TC-A14        | Draft    |
| AI-REQ-15        | UC-02·05·09       | COMP-08·02·12          | AICacheRepository, RateLimiter / ai_cache                                                | API-004·012·013 | SD-01        | TC-A15        | Draft    |

# 부록 A. 설계 검증

강의 5주차 모델 검증(리뷰, 일관성 체크, 요구 추적, 프로토타이핑)과 6주차 설계 원칙으로 점검합니다. 자동 검사는 docs/sdd/tools/sdd_trace.py가 이 문서, SRS, PlantUML 원본을 읽어 수행합니다. '팀 인스펙션' 열은 10/26 회의에서 채웁니다.

자동 검사 8개 중 8개 통과.

| **점검 항목**               | **확인 내용**                                              | **작성자 점검(10/24, 자동 검사 포함)**                                                                                                                                                                          | **팀 인스펙션(10/26)** |
|-----------------------------|------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------|
| 일관성: 유스케이스 ↔ 시퀀스 | SRS에 명세한 유스케이스마다 시퀀스 다이어그램이 있음       | UC-02 → SD-01, UC-05 → SD-02, UC-09 → SD-03, UC-10 → SD-04 (통과)                                                                                                                                               | \[기록\]               |
| 일관성: 시퀀스 ↔ 클래스     | 시퀀스의 객체와 메시지가 클래스 다이어그램에 빠짐없이 있음 | 시퀀스 4개의 클래스 메시지 42개, 라이프라인 클래스 23개가 모두 클래스 다이어그램에 있음 (통과)                                                                                                                  | \[기록\]               |
| 요구 추적                   | FR·NFR·AI-REQ가 모두 설계 요소와 연결됨                    | 요구사항 120개 중 120개가 컴포넌트·Class/DB와 연결 (통과); 추적표의 클래스·연산·테이블·API가 모두 4·5·6장과 3.1 표에 있음 (통과); 추적표의 클래스가 모두 같은 행의 컴포넌트에 속함(SRS 10장과 같은 배정) (통과) | \[기록\]               |
| 계층적 상세화               | 3장의 컴포넌트가 하위 모듈·클래스로 상세화됨               | COMP-01·02는 3.1 모듈 표, 나머지 13개는 CD-01~06 패키지로 상세화 (통과)                                                                                                                                         | \[기록\]               |
| 참조·표기 일관성            | 문서 속 ID가 정의된 것을 가리키고 개수 표기가 실제와 같음  | API 25개, 오류 16개, ADR 14개, SRS ID 참조 모두 정의됨 (통과); 컴포넌트 15개·ADR 14개, 클래스 다이어그램 6개·시퀀스 4개·액티비티 1개, 테이블 16개, API 25개, 오류 16개 (통과)                                   | \[기록\]               |
| 설계 원칙(6주차)            | 높은 응집·낮은 결합, 외부 의존은 어댑터 뒤                 | 3.3에서 컴포넌트별 응집도·결합도 유형 점검, 업무 서비스 간 호출은 RoutePlanner 하나, 외부 접근은 COMP-08·11·12로 한정(작성자 검토)                                                                              | \[기록\]               |
| 과제 조건                   | 단순 LLM 호출이 아님, 부산 실데이터, 출처·이용조건         | AI 요청 1건에 외부 호출 최대 2회와 결정론적 단계 7~9개(7.1), 배치 11단계(COMP-13), 출처 카드 단일 조립(ADR-014), 저장 정책 강제(ADR-004)(작성자 검토)                                                           | \[기록\]               |
| 프로토타이핑                | 모델을 바탕으로 한 시안·PoC                                | 화면 시안 8개(SRS 6.2), 데이터 PoC(10/24, TBD-02~04) 결과로 부록 B 제안값 확정 예정                                                                                                                             | \[기록\]               |

# 부록 B. 확인 필요 사항(제안값)

설계하면서 정한 초기값입니다. 평가셋·부하 시험·PoC 결과로 확정하고, 바뀌면 변경관리 절차(계획서 17.6)를 따릅니다.

| **항목**                            | **제안값**                                | **확정 방법·시점**                         | **관련**  |
|-------------------------------------|-------------------------------------------|--------------------------------------------|-----------|
| 후보 점수 가중치(취향·작품 수·거리) | 0.6 · 0.2 · 0.2                           | 취향 문장 30개 평가(AI-REQ-11), 스프린트 2 | FR-309    |
| 사전 대조 임계값                    | 트라이그램 0.35, 임베딩 코사인 0.75       | 질의 60문항 조건 추출 평가(AI-REQ-10)      | FR-403    |
| AI 요청 제한 시간                   | 조건 추출·구조화 10초, 요약·소개 8초      | 부하 시험(NFR-006)                         | AI-REQ-02 |
| 429 재시도 기준                     | Retry-After 2초 이하만 같은 공급자 재시도 | 장애 주입 시험(NFR-002)                    | AI-REQ-02 |
| 관리자 세션 유효 시간               | 2시간                                     | 팀 합의                                    | FR-615    |
| 환승역 노선 간 이동 시간            | 데이터에 있으면 사용, 없으면 0분          | 역간 소요시간 데이터 확인(TBD-06)          | BR-12     |
| KMDb 저장 정책                      | 설정값(STORE 또는 ID_ONLY)                | 약관 원문 확인(TBD-01)                     | ADR-007   |
| Gemini 무료 모델명·한도             | 설정값                                    | AI Studio 확인(TBD-05)                     | 7.2       |
| API 워커 수                         | 1개                                       | 부하 시험(NFR-001·006) 결과로 재검토       | ADR-013   |

# 부록 C. AI 활용 내역

강의계획서 규정에 따라 이 문서에 쓴 AI 도구의 이름, 사용 일시, 입력 프롬프트, 활용 범위를 밝힙니다. 프로젝트 전체 기록은 계획서 부록 A에 있습니다.

| **일시**   | **도구**           | **입력 프롬프트(요약)**                                                                                                                                                                                                  | **활용 범위**                                                                                                                                                                                       | **사람이 한 일**                                                                                                                          |
|------------|--------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| 2026-10-24 | Claude (Anthropic) | "SDD 작성 진행해줘"(예시 SDD는 참고만), "과하거나 불필요한 부분은 빼고 필요한 부분은 보강, 기준은 강의자료": 수업 SDD 템플릿에 계획서의 아키텍처 결정과 SRS v0.1 요구사항을 이어서 설계 명세서 v0.1을 작성해 달라는 요청 | 작성 범위 질의(1~12장 전체로 결정), 컴포넌트·인터페이스·ADR 초안, 클래스·시퀀스·액티비티·ER·컴포넌트·배치 다이어그램과 AI 파이프라인 그림, DB·API·예외·보안·배포·패턴 표, 추적표·설계 검증 스크립트 | 작성 범위 결정, 아키텍처 방향(계획서 ADR-001~010, 기술 스택)과 요구사항(SRS)은 팀이 정함. 초안 검토·수정과 제안값 확정(\[검토자\], 10/26) |
