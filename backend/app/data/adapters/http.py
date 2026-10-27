"""어댑터용 HTTP 클라이언트. httpx는 data/adapters·ai_gateway에서만 쓰므로 배치는 이 함수로 받는다."""

import httpx


def new_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient()
