"""응답 모델 이름이 겹치면 FastAPI가 'app__api__...' 같은 긴 이름을 만들어 프런트 타입이 깨진다."""

from app.main import create_app


def test_no_duplicate_schema_names():
    names = create_app().openapi()["components"]["schemas"]
    assert not [n for n in names if n.startswith("app__")]
