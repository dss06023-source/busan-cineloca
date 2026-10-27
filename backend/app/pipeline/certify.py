"""방문 인증 가능 여부(BR-06, FR-506). 지도 상세(API-006)와 방문 인증(API-016)이 같은 규칙을 쓴다."""

from app.data.models import Location

CERT_BLOCKING_CAUTIONS = {"private", "residential", "school"}  # BR-06


def cert_block_reason(loc: Location) -> str | None:
    """인증 제외 이유. None이면 인증 가능."""
    if loc.lat is None:
        return "no_coords"
    if loc.cert_excluded:
        return "excluded"
    if loc.caution in CERT_BLOCKING_CAUTIONS:
        return loc.caution
    return None
