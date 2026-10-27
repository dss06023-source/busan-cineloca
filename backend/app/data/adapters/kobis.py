"""KobisClient(DATA-05): KOBIS 영화목록 검색(작품 매칭용 movieCd)과 관람등급 실시간 조회(API-003, FR-107).

KOBIS 약관 6조: 실시간 사용만 허용, 복제·저장·재전송 금지. 그래서 응답을 저장하지 않고,
배치는 PolicyGuard를 거쳐 movie_cd(ID_ONLY)만 넘긴다. 픽스처도 손으로 만든 fixtures/fake/kobis/만 쓴다.
"""

from dataclasses import dataclass
from typing import Any

from app.data.adapters.base import BaseApiClient
from app.data.adapters.errors import ResponseFormatError


@dataclass(frozen=True)
class KobisMovie:
    movie_cd: str
    title: str
    title_en: str
    prdt_year: int | None
    open_dt: str | None  # YYYYMMDD, 미개봉이면 None
    directors: tuple[str, ...]


def _year(v: str | None) -> int | None:
    return int(v) if v and v.isdigit() else None


class KobisClient(BaseApiClient[KobisMovie]):
    name = "kobis"
    list_path = "searchMovieList.json"
    info_path = "searchMovieInfo.json"

    def auth_params(self) -> dict[str, str]:
        return {"key": self.key}

    def page_params(self, page: int) -> dict[str, Any]:
        return {"curPage": page, "itemPerPage": self.conf.page_size}

    def check(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            raise ResponseFormatError("kobis: not object")
        if fault := payload.get("faultInfo"):  # 잘못된 키 등은 200 + faultInfo로 온다
            raise ResponseFormatError(f"kobis: fault {fault.get('errorCode')}")

    def parse(self, payload: Any) -> tuple[list[KobisMovie], int]:
        try:
            result = payload["movieListResult"]
            movies = [
                KobisMovie(
                    movie_cd=m["movieCd"],
                    title=m["movieNm"],
                    title_en=m.get("movieNmEn") or "",
                    prdt_year=_year(m.get("prdtYear")),
                    open_dt=m.get("openDt") or None,
                    directors=tuple(d["peopleNm"] for d in m.get("directors") or []),
                )
                for m in result["movieList"]
            ]
            return movies, int(result["totCnt"])
        except (KeyError, TypeError, ValueError):
            raise ResponseFormatError("kobis: movieListResult") from None

    async def search(self, title: str, max_items: int | None = None) -> list[KobisMovie]:
        """제목으로 후보를 찾는다. 매칭(WorkMatcher)은 부르는 쪽이 한다. 한 페이지만 볼 때는 max_items로 줄인다."""
        if max_items is not None:
            payload = await self.request(self.list_path, {"movieNm": title, "curPage": 1, "itemPerPage": max_items})
            return self.parse(payload)[0]
        return await self.fetch_all(movieNm=title)

    async def rating(self, movie_cd: str, timeout_s: float) -> str | None:
        """RatingProvider(ArchiveService). 상세 화면을 막지 않게 재시도 없이 한 번만 부른다."""
        payload = await self.request(self.info_path, {"movieCd": movie_cd}, timeout_s=timeout_s, retries=1)
        try:
            info = payload["movieInfoResult"]["movieInfo"]
            audits = info.get("audits") or []
        except (KeyError, TypeError):
            raise ResponseFormatError("kobis: movieInfoResult") from None
        if info.get("movieCd") is None:  # 없는 코드는 모든 필드가 null인 빈 객체로 온다
            return None
        # 재심의 등으로 여러 건이면 마지막 심의 결과가 현재 등급
        return (audits[-1].get("watchGradeNm") or None) if audits else None
