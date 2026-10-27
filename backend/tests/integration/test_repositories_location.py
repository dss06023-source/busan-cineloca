"""LocationRepository·StationRepository·SourceRepository·SourceRegistry(템플릿 픽스처 기준)."""

import pytest

from app.data.models import Conditions, LocationAttrs, LocationHit, Point, WorkHit
from app.data.repositories.location import LocationRepository
from app.data.repositories.source import SourceRepository
from app.data.repositories.station import StationRepository
from app.support.sources import SourceRegistry, UnknownSource

pytestmark = pytest.mark.integration

SEOMYEON = Point(35.1579, 129.0594)


async def test_search_person_any_station_walk_10(pool):
    # 시연 장면 3의 형태: 인물 + 아무 역에서 걸어서 10분
    hits = await LocationRepository(pool).search(Conditions(person_ids=[1], any_station_walk_min=10))
    assert [(h.name, h.travel_min) for h in hits] == [("서면 젊음의거리", 4)]
    assert isinstance(hits[0], LocationHit) and hits[0].source_ids == ["DATA-01"]


async def test_search_works(pool):
    hits = await LocationRepository(pool).search(Conditions(gus=["수영구", "해운대구"], result_type="WORK"))
    assert all(isinstance(h, WorkHit) for h in hits)
    assert [h.title for h in hits] == ["해운대", "범죄도시"]


async def test_within_radius_with_filter(pool):
    repo = LocationRepository(pool)
    near = await repo.within_radius(SEOMYEON, 3000)
    assert [h.id for h in near] == [3]
    assert await repo.within_radius(SEOMYEON, 3000, Conditions(genres=["재난"])) == []
    # 넓은 반경: 좌표 없는 촬영지(5)와 retired(4)는 빠진다
    far = await repo.within_radius(SEOMYEON, 50000)
    assert {h.id for h in far} == {1, 2, 3}


async def test_get_and_update_attrs(pool, conn):
    repo = LocationRepository(pool)
    loc = await repo.get(2)
    assert loc.name == "광안리해수욕장" and loc.cert_radius_m == 100 and loc.caution == "none"
    assert await repo.get(4) is None  # retired
    updated = await repo.update_attrs(2, LocationAttrs(cert_radius_m=200, safety_note="야간 주의"))
    assert (updated.cert_radius_m, updated.safety_note, updated.caution) == (200, "야간 주의", "none")
    conn.execute("UPDATE location SET cert_radius_m = 100, safety_note = NULL WHERE id = 2")


async def test_stations(pool):
    repo = StationRepository(pool)
    assert (await repo.nearest(Point(35.1557, 129.0598))).id == "119"
    assert await repo.rail_minutes("119", "209") == 18
    assert await repo.rail_minutes("119", "999") is None
    assert (await repo.get("203")).name == "해운대"
    assert len(await repo.all()) == 4


async def test_source_ledger_has_twelve_with_policies(pool):
    sources = await SourceRepository(pool).all()
    assert [s.id for s in sources] == [f"DATA-{i:02d}" for i in range(1, 13)]
    policy = {s.id: s.policy for s in sources}
    assert policy["DATA-05"] == "ID_ONLY" and policy["DATA-07"] == "NO_STORE"


async def test_registry_cards(pool):
    registry = SourceRegistry(SourceRepository(pool))
    await registry.reload()
    cards = registry.cards(["DATA-02", "DATA-01", "DATA-02"])
    assert [c.id for c in cards] == ["DATA-02", "DATA-01"]
    assert cards[0].org == "부산광역시" and cards[0].url.startswith("https://")
    with pytest.raises(UnknownSource):
        registry.cards(["DATA-99"])
    assert len(registry.licenses()) == 12
    assert "통합전산망" in registry.kobis_notice()
