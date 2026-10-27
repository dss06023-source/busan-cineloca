"""공공데이터포털(apis.data.go.kr) 공통: 키 이름, 페이지 매개변수, 오류 응답, items 모양.

오류는 두 가지로 온다(2026-10-27 실제 응답 확인).
- 게이트웨이 오류: HTTP 403 등 + {"OpenAPI_ServiceResponse": {"cmmMsgHeader": {...}}}. 키 오류는 4xx라 다시 안 보냄
- 서비스 오류: HTTP 200 + response.header.resultCode가 성공 코드가 아님
결과가 없으면 items가 빈 문자열("")이고, 한 건이면 item이 목록이 아닌 객체일 수 있다.
"""

from typing import Any

from app.data.adapters.base import BaseApiClient
from app.data.adapters.errors import ResponseFormatError

SUCCESS_CODES = frozenset({"0000", "00"})


def body_items(payload: Any) -> tuple[list[dict], int]:
    """response.body → (item 목록, totalCount)."""
    try:
        body = payload["response"]["body"]
        items = body.get("items") or {}
        item = items.get("item", []) if isinstance(items, dict) else []
        return ([item] if isinstance(item, dict) else list(item)), int(body.get("totalCount") or 0)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ResponseFormatError("data.go.kr: response.body") from None


class DataGoKrClient[T](BaseApiClient[T]):
    def auth_params(self) -> dict[str, str]:
        return {"serviceKey": self.key}

    def page_params(self, page: int) -> dict[str, Any]:
        return {"pageNo": page, "numOfRows": self.conf.page_size, "_type": "json"}

    def check(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            raise ResponseFormatError(f"{self.name}: not object")
        if gw := payload.get("OpenAPI_ServiceResponse"):
            code = (gw.get("cmmMsgHeader") or {}).get("returnReasonCode")
            raise ResponseFormatError(f"{self.name}: gateway error {code}")
        try:
            code = payload["response"]["header"]["resultCode"]
        except (KeyError, TypeError):
            raise ResponseFormatError(f"{self.name}: response.header") from None
        if code not in SUCCESS_CODES:
            raise ResponseFormatError(f"{self.name}: resultCode {code}")
