"""API-019 출처 대장·라이선스(FR-705, UI-09)."""

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.assembler import Assembler
from app.api.deps import get_assembler


class SourceOut(BaseModel):
    id: str
    org: str
    name: str
    url: str
    license: str
    policy: str
    base_date: date | None


class LicenseOut(BaseModel):
    source_id: str
    license: str
    policy: str


class SourcesOut(BaseModel):
    sources: list[SourceOut]
    licenses: list[LicenseOut]
    kobis_notice: str


router = APIRouter(tags=["출처"])


@router.get("/api/sources", response_model=SourcesOut)
async def sources(asm: Assembler = Depends(get_assembler)):
    registry = asm.registry
    await registry.reload()
    return SourcesOut(
        sources=[SourceOut.model_validate(s, from_attributes=True) for s in registry.ledger()],
        licenses=[LicenseOut(**x) for x in registry.licenses()],
        kobis_notice=registry.kobis_notice(),
    )
