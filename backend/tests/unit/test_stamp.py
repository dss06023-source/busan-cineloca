"""Geofence 경계값(BR-07), TokenSigner 변조 거부(NFR-011), StampService 중복·배지(FR-505·508)."""

import base64
import json
import math
import random
from dataclasses import replace

import pytest

from app.data.models import Course, CourseStop, Location, WorkBrief
from app.pipeline.travel import EARTH_R_M
from app.services.stamp import geofence
from app.services.stamp.service import InvalidInput, NotCertifiable, NotFound, StampService, custom_course_key
from app.services.stamp.tokens import BadToken, TokenSigner, parse_keys

LAT, LON = 35.1152, 129.0422


def north(meters: float) -> tuple[float, float]:
    """자오선을 따라 정확히 meters만큼 북쪽 점(하버사인 거리가 그대로 나온다)."""
    return LAT + math.degrees(meters / EARTH_R_M), LON


def fix(meters: float, acc: float = 10) -> geofence.GeoFix:
    return geofence.GeoFix(*north(meters), accuracy_m=acc)


@pytest.mark.parametrize(("d", "ok"), [(99, True), (100, True), (100.5, False), (101, False)])
def test_geofence_radius_boundary(d, ok):
    v = geofence.check(fix(d), LAT, LON, 100)
    assert v.ok is ok and v.reason == (None if ok else "distance")


@pytest.mark.parametrize(("acc", "ok"), [(50, True), (50.1, False), (51, False)])
def test_geofence_accuracy_boundary(acc, ok):
    v = geofence.check(fix(10, acc), LAT, LON, 100)
    assert v.ok is ok and v.reason == (None if ok else "accuracy")


def test_geofence_custom_radius_and_distance_reported():
    assert geofence.check(fix(250), LAT, LON, 300).ok
    v = geofence.check(fix(250), LAT, LON, 50)
    assert not v.ok and v.distance_m == 250


KEYS = {"k2": b"n" * 32, "k1": b"o" * 32}


def signer(keys=KEYS, now=1_800_000_000) -> TokenSigner:
    return TokenSigner(keys, clock=lambda: now)


def _parts(token: str) -> tuple[dict, dict, str]:
    h, p, s = token.split(".")
    dec = lambda x: json.loads(base64.urlsafe_b64decode(x + "=" * (-len(x) % 4)))  # noqa: E731
    return dec(h), dec(p), s


def _enc(d: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).rstrip(b"=").decode()


def test_stamp_claims_have_no_coordinates_or_expiry():
    t = signer().stamp(9)
    head, body, _ = _parts(t)
    assert head == {"alg": "HS256", "typ": "JWT"}
    assert body == {"typ": "stamp", "loc": 9, "iat": 1_800_000_000, "kid": "k2"}
    assert signer().verify(t, "stamp").loc == 9


def test_old_kid_token_still_verifies_after_rotation():
    old = signer({"k1": KEYS["k1"]}).stamp(3)
    assert signer().verify(old, "stamp").kid == "k1"
    with pytest.raises(BadToken):  # 키를 뺀 뒤에는 거부
        signer({"k2": KEYS["k2"]}).verify(old, "stamp")


def test_rejects_100_tampered_tokens():
    s = signer()
    good = s.stamp(9)
    h, p, sig = good.split(".")
    head, body, _ = _parts(good)
    rnd = random.Random(11)
    tampered: set[str] = set()
    # 페이로드 변조(장소·시각·종류·키 바꾸기, 클레임 추가)
    for loc in range(1, 31):
        tampered.add(f"{h}.{_enc({**body, 'loc': loc + 100})}.{sig}")
    for d in range(1, 21):
        tampered.add(f"{h}.{_enc({**body, 'iat': body['iat'] - d})}.{sig}")
    tampered.add(f"{h}.{_enc({**body, 'typ': 'badge'})}.{sig}")
    tampered.add(f"{h}.{_enc({**body, 'kid': 'k1'})}.{sig}")
    tampered.add(f"{h}.{_enc({**body, 'kid': 'zz'})}.{sig}")
    tampered.add(f"{h}.{_enc({**body, 'lat': 35.1})}.{sig}")
    # alg 바꾸기·서명 없음
    tampered.add(f"{_enc({**head, 'alg': 'none'})}.{p}.")
    tampered.add(f"{_enc({**head, 'alg': 'HS512'})}.{p}.{sig}")
    tampered.add(f"{h}.{p}.")
    # 다른 키로 서명
    tampered.add(signer({"k2": b"x" * 32}).stamp(9))
    # 서명 글자 바꾸기
    while len(tampered) < 90:
        i = rnd.randrange(len(sig))
        c = rnd.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        if c != sig[i]:
            tampered.add(f"{h}.{p}.{sig[:i]}{c}{sig[i + 1 :]}")
    # 형식이 깨진 것
    tampered |= {"", ".", "..", "a.b.c", good + ".x", good[:-1], h, f"{h}.{p}", "x" * 40, f"{p}.{h}.{sig}"}
    assert len(tampered) >= 100
    for t in tampered:
        with pytest.raises(BadToken):
            s.verify(t, "stamp")


def test_stamp_token_is_not_a_badge():
    s = signer()
    with pytest.raises(BadToken):
        s.verify(s.stamp(9), "badge")
    assert s.verify(s.badge("course:1"), "badge").course_key == "course:1"


@pytest.mark.parametrize("spec", ["", "k1", "k1:short", ":" + "a" * 32, "k1:" + "a" * 31])
def test_parse_keys_rejects_bad_spec(spec):
    with pytest.raises(ValueError):
        parse_keys(spec)


def test_parse_keys_keeps_order():
    assert list(parse_keys(f"new:{'a' * 32}, old:{'b' * 40}")) == ["new", "old"]


def test_custom_course_key_ignores_order_and_duplicates():
    assert custom_course_key([3, 1, 2]) == custom_course_key([1, 2, 3, 3])
    assert custom_course_key([1, 2]) != custom_course_key([1, 3])


# ---- StampService(가짜 저장소) ----


def loc(i: int, **kw) -> Location:
    base = Location(i, f"L{i}", None, "동구", LAT, LON, [], "none", None, 100, False, None, None)
    return replace(base, **kw)


class FakeLocations:
    def __init__(self, items):
        self.items = {x.id: x for x in items}

    async def get(self, i):
        return self.items.get(i)

    async def many(self, ids):
        return [self.items[i] for i in ids if i in self.items]


class FakeWorks:
    async def by_locations(self, ids):
        return {i: [WorkBrief(1, "부산 추격전", 2017)] if i == 1 else [] for i in ids}


class FakeCourses:
    async def get(self, i):
        stops = [CourseStop(1, 1), CourseStop(2, 2)]
        if i == 1:
            return Course("work", "t", "부산역", LAT, LON, 10, 10, stops, status="approved", id=1)
        if i == 2:
            return Course("work", "t", "부산역", LAT, LON, 10, 10, stops, status="draft", id=2)
        return None


@pytest.fixture
def svc():
    items = [loc(1), loc(2), loc(3, lat=None, lon=None), loc(4, cert_excluded=True), loc(5, caution="private")]
    return StampService(FakeLocations(items), FakeWorks(), FakeCourses(), signer())


async def test_certify_issues_token_then_blocks_duplicate(svc):
    r = await svc.certify(1, fix(30), held=[])
    assert r.ok and r.reason is None and r.distance_m == 30
    again = await svc.certify(1, fix(30), held=[r.token, "garbage"])
    assert not again.ok and again.reason == "duplicate" and again.token is None


async def test_certify_failures(svc):
    far = await svc.certify(1, fix(150), held=[])
    assert (far.ok, far.reason, far.distance_m) == (False, "distance", 150)
    with pytest.raises(NotFound):
        await svc.certify(99, fix(0), held=[])
    for i, reason in [(3, "no_coords"), (4, "excluded"), (5, "private")]:
        with pytest.raises(NotCertifiable) as e:
            await svc.certify(i, fix(0), held=[])
        assert e.value.reason == reason


async def test_verify_counts_invalid_and_unknown_locations(svc):
    s = svc.signer
    tokens = [s.stamp(1), s.stamp(1), s.stamp(2), s.stamp(77), "bad"]
    r = await svc.verify(tokens)
    assert [e.location.id for e in r.valid] == [1, 2]
    assert r.valid[0].work and r.valid[0].work.title == "부산 추격전"
    assert r.invalid_count == 2  # 'bad'와 없는 촬영지 77


async def test_badge_recommended_and_custom(svc):
    s = svc.signer
    part = await svc.issue_badge(1, None, [s.stamp(1)])
    assert not part.ok and part.missing == [2]
    full = await svc.issue_badge(1, None, [s.stamp(1), s.stamp(2)])
    assert full.ok and s.verify(full.token, "badge").course_key == "course:1"
    custom = await svc.issue_badge(None, [2, 1], [s.stamp(1), s.stamp(2)])
    assert custom.ok and custom.course_key == custom_course_key([1, 2])
    with pytest.raises(NotFound):
        await svc.issue_badge(2, None, [])  # 초안 코스
    with pytest.raises(InvalidInput):
        await svc.issue_badge(None, [1], [])
    forged = await svc.issue_badge(1, None, [signer({"k2": b"x" * 32}).stamp(1), s.stamp(2)])
    assert not forged.ok and forged.missing == [1]
