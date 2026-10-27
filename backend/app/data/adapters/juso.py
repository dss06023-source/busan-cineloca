"""JusoGeocoder(DATA-06): 주소 → 위경도. 행정안전부 도로명주소 검색 API로 도로명코드·건물번호를 찾고,
좌표제공 API로 그 건물의 좌표(UTM-K, EPSG:5179)를 받아 WGS84로 바꾼다(build-plan 7장 '좌표 받기와 변환').

두 API는 승인키가 따로다(JUSO_KEY, JUSO_COORD_KEY). 응답 형식은 사용자가 받은 활용 가이드와
가이드의 테스트 승인키(TESTJUSOGOKR, 요청과 상관없이 고정 예시를 줌)로 받은
실제 응답(fixtures/real/juso/)으로 확인했다.
오류는 HTTP 200 + results.common.errorCode(정상 '0')로 온다.
"""

import re
from dataclasses import dataclass
from typing import Any

from pyproj import Transformer

from app.data.adapters.base import BaseApiClient
from app.data.adapters.errors import ResponseFormatError

SOURCE_ID = "DATA-06"
BUSAN = "부산광역시"
_UTMK_TO_WGS84 = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)
_PAREN = re.compile(r"\([^)]*\)")
# 검색 API가 거부하는 문자(가이드 E0013)
_FORBIDDEN = re.compile(r"[%=><\[\]]")
MAX_KEYWORD = 40  # 한글 40자(가이드 E0010)


def utmk_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """UTM-K(x=동, y=북) → (위도, 경도)."""
    lon, lat = _UTMK_TO_WGS84.transform(x, y)
    return lat, lon


def clean_keyword(address: str) -> str:
    """'부산 남구 유엔평화로 63 (대연동, 부산박물관)' → '부산 남구 유엔평화로 63'. 괄호 안 참고항목은 검색을 흐린다."""
    s = _FORBIDDEN.sub(" ", _PAREN.sub(" ", address))
    return " ".join(s.split())[:MAX_KEYWORD]


@dataclass(frozen=True)
class JusoAddress:
    road_addr: str
    sido: str
    gu: str
    adm_cd: str
    rn_mgt_sn: str
    udrt_yn: str
    buld_mnnm: str
    buld_slno: str


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lon: float
    road_addr: str
    gu: str
    source_id: str = SOURCE_ID


def _results(payload: Any) -> tuple[dict, list[dict]]:
    try:
        res = payload["results"]
        return res["common"], res.get("juso") or []
    except (KeyError, TypeError):
        raise ResponseFormatError("juso: results") from None


class _JusoClient[T](BaseApiClient[T]):
    def auth_params(self) -> dict[str, str]:
        return {"confmKey": self.key}

    def check(self, payload: Any) -> None:
        common, _ = _results(payload)
        if (code := str(common.get("errorCode"))) != "0":
            raise ResponseFormatError(f"{self.name}: errorCode {code}")


class JusoSearchClient(_JusoClient[JusoAddress]):
    name = "juso_search"
    list_path = "addrLinkApi.do"

    def page_params(self, page: int) -> dict[str, Any]:
        return {"currentPage": page, "countPerPage": self.conf.page_size, "resultType": "json"}

    def parse(self, payload: Any) -> tuple[list[JusoAddress], int]:
        common, items = _results(payload)
        try:
            rows = [
                JusoAddress(
                    road_addr=i["roadAddrPart1"],
                    sido=i["siNm"],
                    gu=i["sggNm"],
                    adm_cd=i["admCd"],
                    rn_mgt_sn=i["rnMgtSn"],
                    udrt_yn=i["udrtYn"],
                    buld_mnnm=str(i["buldMnnm"]),
                    buld_slno=str(i["buldSlno"]),
                )
                for i in items
            ]
            return rows, int(common.get("totalCount") or 0)
        except (KeyError, TypeError, ValueError):
            raise ResponseFormatError("juso_search: juso") from None

    async def first(self, keyword: str) -> list[JusoAddress]:
        """첫 페이지만. 주소 하나를 찾는 데 페이지를 넘길 일은 없다."""
        return self.parse(await self.request(self.list_path, {"keyword": keyword, **self.page_params(1)}))[0]


class JusoCoordClient(_JusoClient[tuple[float, float]]):
    name = "juso_coord"
    list_path = "addrCoordApi.do"

    def page_params(self, page: int) -> dict[str, Any]:
        return {"resultType": "json"}

    def parse(self, payload: Any) -> tuple[list[tuple[float, float]], int]:
        common, items = _results(payload)
        try:
            pts = [(float(i["entX"]), float(i["entY"])) for i in items if i.get("entX") and i.get("entY")]
            return pts, int(common.get("totalCount") or 0)
        except (KeyError, TypeError, ValueError):
            raise ResponseFormatError("juso_coord: juso") from None

    async def utmk(self, a: JusoAddress) -> tuple[float, float] | None:
        params = {
            "admCd": a.adm_cd,
            "rnMgtSn": a.rn_mgt_sn,
            "udrtYn": a.udrt_yn,
            "buldMnnm": a.buld_mnnm,
            "buldSlno": a.buld_slno,
            **self.page_params(1),
        }
        pts, _ = self.parse(await self.request(self.list_path, params))
        return pts[0] if pts else None


class JusoGeocoder:
    """주소 하나 → GeoPoint. 못 찾거나 부산이 아니면 None(geocode_status = failed, 관리자 보정 대상)."""

    def __init__(self, search: JusoSearchClient, coord: JusoCoordClient, sido: str | None = BUSAN):
        self.search, self.coord, self.sido = search, coord, sido

    async def geocode(self, address: str) -> GeoPoint | None:
        keyword = clean_keyword(address)
        if not keyword:
            return None
        hits = [a for a in await self.search.first(keyword) if self.sido is None or a.sido == self.sido]
        if not hits:
            return None
        a = hits[0]
        xy = await self.coord.utmk(a)
        if xy is None:
            return None
        lat, lon = utmk_to_wgs84(*xy)
        return GeoPoint(lat=lat, lon=lon, road_addr=a.road_addr, gu=a.gu)
