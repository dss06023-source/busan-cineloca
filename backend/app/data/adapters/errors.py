"""어댑터 오류. ProviderError를 이어받아 서비스는 AI 공급자와 같은 방식으로 강등한다.

메시지에는 상태 코드와 기관 오류 코드만 넣는다. 요청 URL에는 키가 들어 있으므로 httpx 예외를 그대로 잇지 않는다.
"""

from app.data.ai_gateway.errors import ProviderError


class AdapterError(ProviderError):
    """5xx·연결 실패·시간 초과가 재시도 뒤에도 남음."""


class AdapterTimeout(AdapterError):
    pass


class ResponseFormatError(AdapterError):
    """응답이 JSON이 아니거나, 기관 오류 응답이거나, 기대한 구조가 아님."""


class QuotaExhausted(AdapterError):
    """오늘 호출 수가 하루 한도의 80%에 닿음. 부르지 않고 멈춘다(NFR-018)."""
