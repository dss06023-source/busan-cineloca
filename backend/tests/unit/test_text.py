from app.data.text import normalize


def test_normalize():
    assert normalize("마 동석") == "마동석"
    assert normalize("범죄도시 2") == "범죄도시2"
    assert normalize("ＡＢＣ·해운대!") == "abc해운대"
