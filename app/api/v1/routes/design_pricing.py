from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.design_pricing import DesignPricingConfigCreate, DesignPricingConfigRead
from app.services.design_pricing import DesignPricingConfigService

router = APIRouter(prefix="/design-pricing-configs", tags=["design-pricing-configs"])


@router.get("", response_model=list[DesignPricingConfigRead])
def list_design_pricing_configs(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    business_type: str = Query(default="design"),
    status_filter: str = Query(default="active", alias="status"),
):
    return DesignPricingConfigService(db).list_active_configs(
        business_type=business_type,
        status=status_filter,
    )


@router.post("", response_model=DesignPricingConfigRead, status_code=status.HTTP_201_CREATED)
def create_design_pricing_config(
    payload: DesignPricingConfigCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return DesignPricingConfigService(db).create_config(payload)
