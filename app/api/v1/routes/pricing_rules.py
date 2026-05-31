from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.pricing_rule import (
    PricingRuleCreate,
    PricingRuleImportResponse,
    PricingRuleRead,
)
from app.services.pricing_rules import PricingRuleService

router = APIRouter(prefix="/pricing-rules", tags=["pricing-rules"])


@router.get("", response_model=list[PricingRuleRead])
def list_pricing_rules(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    country_region: str | None = Query(default=None),
    patent_type: str | None = Query(default=None),
    filing_route: str | None = Query(default=None),
    currency: str | None = Query(default=None),
    status_filter: str = Query(default="active", alias="status"),
):
    return PricingRuleService(db).list_active_rules(
        country_region=country_region,
        patent_type=patent_type,
        filing_route=filing_route,
        currency=currency,
        status=status_filter,
    )


@router.post("", response_model=PricingRuleRead, status_code=status.HTTP_201_CREATED)
def create_pricing_rule(
    payload: PricingRuleCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return PricingRuleService(db).create_rule(payload)


@router.post("/import", response_model=PricingRuleImportResponse)
async def import_pricing_rules(
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    content = await file.read()
    service = PricingRuleService(db)
    try:
        imported_count, skipped_count = service.import_rules(
            filename=file.filename or "pricing_rules",
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PricingRuleImportResponse(
        filename=file.filename or "pricing_rules",
        message="规则导入完成。",
        imported_count=imported_count,
        skipped_count=skipped_count,
    )
