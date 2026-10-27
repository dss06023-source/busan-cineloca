"""TourPhotoClient(DATA-10): TourAPI 4.0 국문(KorService2) 위치기반 관광정보로 촬영지 주변 사진 후보를 찾는다.

대표 이미지는 공공누리 제1유형(cpyrhtDivCd = 'Type1')만 쓴다(BR-03, photo.kogl_type CHECK = 1).
이미지 파일은 받지 않고 주소만 넘긴다. 응답 필드는 2026-10-27 실제 응답(fixtures/real/tourapi/)으로 확인했다.
"""

from dataclasses import dataclass
from typing import Any

from app.data.adapters.data_go_kr import DataGoKrClient, body_items
from app.data.adapters.errors import ResponseFormatError

SOURCE_ID = "DATA-10"
ATTRACTION = "12"  # contentTypeId 관광지


@dataclass(frozen=True)
class TourPlace:
    content_id: str
    title: str
    address: str | None
    lat: float
    lon: float
    dist_m: float | None
    image_url: str | None
    kogl_type: int | None  # 'Type1' → 1, 'Type3' → 3, 없으면 None

    @property
    def usable_photo(self) -> bool:
        return self.kogl_type == 1 and bool(self.image_url)


def _kogl(v: str | None) -> int | None:
    return int(v[4:]) if v and v.startswith("Type") and v[4:].isdigit() else None


def _float(v: Any) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


class TourPhotoClient(DataGoKrClient[TourPlace]):
    name = "tourapi"
    list_path = "locationBasedList2"

    def page_params(self, page: int) -> dict[str, Any]:
        return {**super().page_params(page), "MobileOS": "ETC", "MobileApp": "cineloca"}

    def parse(self, payload: Any) -> tuple[list[TourPlace], int]:
        items, total = body_items(payload)
        try:
            places = [
                TourPlace(
                    content_id=str(i["contentid"]),
                    title=i["title"],
                    address=" ".join(p for p in (i.get("addr1"), i.get("addr2")) if p) or None,
                    lat=float(i["mapy"]),
                    lon=float(i["mapx"]),
                    dist_m=_float(i.get("dist")),
                    image_url=i.get("firstimage") or None,
                    kogl_type=_kogl(i.get("cpyrhtDivCd")),
                )
                for i in items
            ]
        except (KeyError, TypeError, ValueError):
            raise ResponseFormatError("tourapi: item") from None
        return places, total

    async def near(
        self, lat: float, lon: float, radius_m: int = 1000, content_type: str | None = ATTRACTION
    ) -> list[TourPlace]:
        """거리순 주변 관광지. 반경은 TourAPI 상한 20km 안에서."""
        query = {"mapX": f"{lon:.7f}", "mapY": f"{lat:.7f}", "radius": min(int(radius_m), 20000), "arrange": "E"}
        if content_type:
            query["contentTypeId"] = content_type
        return await self.fetch_all(**query)

    async def photos_near(self, lat: float, lon: float, radius_m: int = 1000) -> list[TourPlace]:
        """사진으로 쓸 수 있는(제1유형, 이미지 있음) 장소만."""
        return [p for p in await self.near(lat, lon, radius_m) if p.usable_photo]
