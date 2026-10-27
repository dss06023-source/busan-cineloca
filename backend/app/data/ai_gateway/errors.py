"""게이트웨이 오류. 기능 코드는 AIUnavailable 하나만 받고 강등 처리한다."""


class AIUnavailable(Exception):
    """모든 공급자가 실패했거나 시간이 모자람(ERR-003). 부른 쪽이 강등 응답을 만든다."""

    def __init__(self, task: str, reasons: list[str] | None = None):
        self.task = task
        self.reasons = reasons or []
        super().__init__(f"{task}: {', '.join(self.reasons) or 'unavailable'}")


class ProviderError(Exception):
    """5xx·연결 실패·응답 형식 이상."""


class ProviderTimeout(ProviderError):
    pass


class RateLimited(ProviderError):
    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(f"429 retry_after={retry_after}")


class SchemaError(ProviderError):
    """출력이 JSON이 아니거나 스키마를 어김(ERR-004)."""
