"""질의·취향 문장 임베딩(bge-m3, 1024차원). 실패하면 부른 쪽이 트라이그램·태그 일치만 쓴다."""

import hashlib
import math
import random

import httpx

from app.data.ai_gateway.errors import ProviderError, ProviderTimeout


class OllamaEmbedder:
    def __init__(self, base_url: str, client: httpx.AsyncClient, model: str = "bge-m3", timeout_s: float = 1.5):
        self.url = base_url.rstrip("/") + "/api/embed"
        self.client = client
        self.model = model
        self.timeout_s = timeout_s

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            res = await self.client.post(
                self.url, json={"model": self.model, "input": texts}, timeout=httpx.Timeout(self.timeout_s)
            )
        except httpx.TimeoutException:
            raise ProviderTimeout("embed") from None
        except httpx.HTTPError as e:
            raise ProviderError(type(e).__name__) from None
        if res.status_code >= 400:
            raise ProviderError(f"HTTP {res.status_code}")
        vectors = res.json().get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise ProviderError("embeddings 개수 불일치")
        return vectors


class FakeEmbedder:
    """텍스트 해시를 씨앗으로 만든 단위 벡터. 같은 입력이면 늘 같은 벡터(build-plan 9장)."""

    def __init__(self, dim: int = 1024):
        self.dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            rng = random.Random(int.from_bytes(hashlib.sha256(t.encode()).digest()[:8], "big"))
            v = [rng.gauss(0, 1) for _ in range(self.dim)]
            n = math.sqrt(sum(x * x for x in v))
            out.append([x / n for x in v])
        return out
