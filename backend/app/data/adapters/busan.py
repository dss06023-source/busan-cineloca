"""부산 원본 3종(apis.data.go.kr). 응답 필드는 2026-10-27 실제 응답(fixtures/real/)으로 확인했다.

- FilmLocationClient(DATA-01, 부산영상위원회 영화 속 부산정보): 작품명·장소명·개봉일. 주소와 좌표가 없다
- CineMapClient(DATA-02, 부산영상위원회 씨네맵): 작품명·장소명·도로명주소. 좌표가 없다
- StationClient(DATA-08, 부산교통공사 역사정보): 역 코드·역명·주소·전화. 호선과 좌표가 없다
좌표는 주소 좌표 API(DATA-06)로, 장소명만 있는 레코드는 같은 장소의 씨네맵 주소나 관리자 보정으로 채운다(WP-07).
"""

from dataclasses import dataclass
from typing import Any

from app.data.adapters.data_go_kr import DataGoKrClient, body_items
from app.data.adapters.errors import ResponseFormatError


@dataclass(frozen=True)
class FilmLocation:
    source_id: str
    work_title: str
    place_name: str
    address: str | None = None
    release_date: str | None = None  # YYYY-MM-DD


@dataclass(frozen=True)
class StationRecord:
    code: str
    name: str
    address: str | None
    tel: str | None


def _s(v: Any) -> str | None:
    v = str(v).strip() if v is not None else ""
    return v or None


class _BusanCityClient(DataGoKrClient[FilmLocation]):
    format_params = {"resultType": "json"}
    source_id = ""

    def to_record(self, i: dict) -> FilmLocation:
        raise NotImplementedError

    def parse(self, payload: Any) -> tuple[list[FilmLocation], int]:
        items, total = body_items(payload)
        try:
            return [self.to_record(i) for i in items], total
        except (KeyError, TypeError, AttributeError):
            raise ResponseFormatError(f"{self.name}: item") from None


class FilmLocationClient(_BusanCityClient):
    name = "bfc_movie"
    source_id = "DATA-01"
    list_path = "getBfcMovieBusan"

    def to_record(self, i: dict) -> FilmLocation:
        return FilmLocation(
            source_id=self.source_id,
            work_title=i["opusNm"].strip(),
            place_name=i["plcNm"].strip(),
            release_date=_s(i.get("opnDay")),
        )


class CineMapClient(_BusanCityClient):
    name = "cinemap"
    source_id = "DATA-02"
    list_path = "getCineMap"

    def to_record(self, i: dict) -> FilmLocation:
        return FilmLocation(
            source_id=self.source_id,
            work_title=i["opusNm"].strip(),
            place_name=i["plcNm"].strip(),
            address=_s(i.get("roadNmAddr")),
        )


class StationClient(DataGoKrClient[StationRecord]):
    name = "station"
    list_path = "getStationInfo"

    def parse(self, payload: Any) -> tuple[list[StationRecord], int]:
        items, total = body_items(payload)
        try:
            stations = [
                StationRecord(
                    code=str(i["scode"]), name=i["sname"].strip(), address=_s(i.get("saddr")), tel=_s(i.get("stel"))
                )
                for i in items
            ]
        except (KeyError, TypeError, AttributeError):
            raise ResponseFormatError("station: item") from None
        return stations, total
