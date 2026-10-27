# KOBIS 가짜 응답

KOBIS 응답 본문은 저장 금지(약관 6조, AGENTS.md)라서 실제 응답을 복사하지 않았다.
2026-10-27에 실제 API를 한 번 불러 필드 이름과 구조만 확인하고, 값은 손으로 지어 넣었다.

- movie_list_p1.json, movie_list_p2.json: searchMovieList.json 두 페이지(totCnt 3, itemPerPage 2)
- movie_info.json: searchMovieInfo.json, 심의 2건(마지막 것이 현재 등급)
- movie_info_empty.json: 없는 movieCd를 넣으면 오는 모양(모든 필드 null)
- fault.json: 잘못된 키(HTTP 200 + faultInfo)
