"""배치 로그에 외부 API 키가 남지 않는다: httpx의 요청 URL 로그(INFO)를 끈다."""

import logging

import httpx
import pytest
import respx

from app.batch.__main__ import configure_logging

KEY = "secret-service-key-for-test"


@respx.mock
async def test_request_url_with_key_is_not_logged(caplog: pytest.LogCaptureFixture):
    respx.get("https://apis.data.go.kr/x").mock(return_value=httpx.Response(200, json={}))
    configure_logging()
    with caplog.at_level(logging.INFO):
        async with httpx.AsyncClient() as c:
            await c.get("https://apis.data.go.kr/x", params={"serviceKey": KEY})
    assert KEY not in caplog.text
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
