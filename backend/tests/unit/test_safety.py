"""PrivacyGuard(가짜 개인정보 50건 100%), GroundingVerifier, PhraseFilter."""

import json
from pathlib import Path

from app.support.grounding import EntityLexicon, GroundingVerifier, PhraseFilter
from app.support.privacy import MASK, mask, mask_inputs, scrub

PII = json.loads((Path(__file__).parents[1] / "fixtures/fake/pii.json").read_text(encoding="utf-8"))["records"]


def test_pii_fixture_all_masked():
    assert len(PII) == 50
    for r in PII:
        out, kinds = mask(r["text"])
        assert r["value"] not in out, r
        assert MASK in out and kinds == [r["kind"]], (r, kinds)


def test_mask_keeps_ordinary_numbers():
    text = "1990년 영화, 서면역에서 15분, 2호선, 1.2km"
    assert mask(text) == (text, [])


def test_mask_inputs_drops_coordinates_and_reports_kinds():
    masked, kinds = mask_inputs(
        {"user_input": "010-1234-5678 해운대", "base": {"lat": 35.1, "lng": 129.1, "kind": "current"}}
    )
    assert masked == {"user_input": f"{MASK} 해운대", "base": {"kind": "current"}}
    assert kinds == ["phone"]


def test_scrub_nested():
    assert scrub({"a": ["x@example.com"], "n": 3}) == {"a": [MASK], "n": 3}


LEX = EntityLexicon(["가상 영화 A", "가상 영화 A2", "가상 부두", "가상 시장", "영도구", "중구", "강도윤"])
EVIDENCE = {
    "work": {"id": 1, "source_id": "DEV-SEED", "title": "가상 영화 A", "year": 2019},
    "locations": [{"id": 4, "name": "가상 부두", "gu": "영도구", "walk_min": 12, "distance_m": 850}],
    "persons": ["강도윤"],
}
V = GroundingVerifier(LEX, PhraseFilter(["결말", "범인은"]))


def s(text, *entities):
    return {"text": text, "entities": list(entities)}


def test_gate_empty_evidence():
    assert not GroundingVerifier.gate({"locations": [], "work": None})
    assert not GroundingVerifier.gate([])
    assert GroundingVerifier.gate(EVIDENCE)


def test_verify_keeps_grounded_sentences():
    out = V.verify(
        [
            s("「가상 영화 A」(2019년)는 영도구의 가상 부두에서 찍었습니다.", "가상 영화 A", "2019", "가상 부두"),
            s("역에서 걸어서 12분, 850m 거리입니다."),
            s("강도윤이 출연했습니다.", "강도윤"),
        ],
        EVIDENCE,
    )
    assert len(out.sentences) == 3 and out.dropped == []


def test_verify_drops_unknown_entity_from_lexicon():
    out = V.verify([s("중구의 가상 시장에서도 찍었습니다.")], EVIDENCE)
    assert out.sentences == [] and out.dropped[0]["reason"].startswith("entity:")


def test_verify_drops_model_entity_not_in_evidence():
    out = V.verify([s("유명 배우가 나옵니다.", "마동석")], EVIDENCE)
    assert out.dropped[0]["reason"] == "entity:마동석"


def test_verify_drops_unknown_numbers():
    out = V.verify([s("2021년에 개봉했습니다."), s("걸어서 20분 걸립니다."), s("3km 떨어져 있습니다.")], EVIDENCE)
    assert [d["reason"] for d in out.dropped] == ["number:2021", "number:20", "number:3"]


def test_longer_name_not_counted_as_shorter():
    out = V.verify([s("「가상 영화 A2」도 있습니다.")], EVIDENCE)
    assert out.dropped[0]["reason"] == "entity:가상 영화 A2"


def test_phrase_filter_drops_spoilers_unless_disabled():
    sent = [s("결말에서 가상 부두가 다시 나옵니다.", "가상 부두")]
    assert V.verify(sent, EVIDENCE).dropped[0]["reason"] == "phrase:결말"
    assert len(V.verify(sent, EVIDENCE, spoiler_check=False).sentences) == 1


def test_phrase_filter_config_loads():
    f = PhraseFilter.from_config()
    assert f.hit("알고 보니 범인은 그였다") and f.hit("부산 바다") is None
