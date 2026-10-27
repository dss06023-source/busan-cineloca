"""TokenSigner(NFR-011): 스탬프·배지 토큰을 HS256 JWT로 서명하고 확인한다.

클레임은 stamp {typ, loc, iat, kid}, badge {typ, course_key, iat, kid}이다(SDD 5.2).
좌표와 만료는 넣지 않는다. 키는 TOKEN_KEYS="kid:비밀,kid:비밀"에서 읽고 앞의 것으로 서명한다.
뒤의 키는 교체 전에 발급한 토큰 확인용이다.
"""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

_HEADER = {"alg": "HS256", "typ": "JWT"}
MIN_SECRET_BYTES = 32


class BadToken(Exception):
    pass


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def parse_keys(spec: str) -> dict[str, bytes]:
    """'kid:비밀,kid:비밀' → 순서를 지킨 dict. 비밀이 짧으면 거부한다."""
    keys: dict[str, bytes] = {}
    for part in filter(None, (p.strip() for p in spec.split(","))):
        kid, sep, secret = part.partition(":")
        if not sep or not kid or len(secret.encode()) < MIN_SECRET_BYTES:
            raise ValueError(f"TOKEN_KEYS 형식은 kid:비밀({MIN_SECRET_BYTES}바이트 이상)입니다")
        keys[kid] = secret.encode()
    if not keys:
        raise ValueError("TOKEN_KEYS가 비었습니다")
    return keys


@dataclass(frozen=True)
class Claims:
    typ: str
    iat: int
    kid: str
    loc: int | None = None
    course_key: str | None = None


class TokenSigner:
    def __init__(self, keys: dict[str, bytes], clock=time.time):
        if not keys:
            raise ValueError("서명 키가 없습니다")
        self.keys = keys
        self.current = next(iter(keys))
        self.clock = clock

    def _sign(self, kid: str, signing_input: bytes) -> str:
        return _b64(hmac.new(self.keys[kid], signing_input, hashlib.sha256).digest())

    def issue(self, typ: str, **claims) -> str:
        body = {"typ": typ, **claims, "iat": int(self.clock()), "kid": self.current}
        head = _b64(json.dumps(_HEADER, separators=(",", ":")).encode())
        payload = _b64(json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode())
        signing_input = f"{head}.{payload}".encode()
        return f"{head}.{payload}.{self._sign(self.current, signing_input)}"

    def stamp(self, location_id: int) -> str:
        return self.issue("stamp", loc=location_id)

    def badge(self, course_key: str) -> str:
        return self.issue("badge", course_key=course_key)

    def verify(self, token: str, typ: str) -> Claims:
        """서명·형식·종류가 맞으면 Claims, 아니면 BadToken. 값은 예외 문구에 넣지 않는다."""
        try:
            head_s, payload_s, sig_s = token.split(".")
            head = json.loads(_unb64(head_s))
            body = json.loads(_unb64(payload_s))
        except Exception:
            raise BadToken("형식") from None
        if head != _HEADER or not isinstance(body, dict):
            raise BadToken("헤더")
        kid = body.get("kid")
        if not isinstance(kid, str) or kid not in self.keys:
            raise BadToken("키")
        if not hmac.compare_digest(self._sign(kid, f"{head_s}.{payload_s}".encode()), sig_s):
            raise BadToken("서명")
        if body.get("typ") != typ or not isinstance(body.get("iat"), int):
            raise BadToken("종류")
        if typ == "stamp" and not (isinstance(body.get("loc"), int) and set(body) == {"typ", "loc", "iat", "kid"}):
            raise BadToken("클레임")
        if typ == "badge" and not (
            isinstance(body.get("course_key"), str) and set(body) == {"typ", "course_key", "iat", "kid"}
        ):
            raise BadToken("클레임")
        return Claims(typ=typ, iat=body["iat"], kid=kid, loc=body.get("loc"), course_key=body.get("course_key"))
