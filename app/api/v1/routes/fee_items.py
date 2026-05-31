from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.fee_item import FeeItemDefinitionCreate, FeeItemDefinitionRead
from app.services.fee_items import FeeItemDefinitionService

router = APIRouter(prefix="/fee-items", tags=["fee-items"])


class FeeItemEnabledUpdate(BaseModel):
    is_enabled: bool


@router.get("", response_model=list[FeeItemDefinitionRead])
def list_fee_items(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    business_type: str | None = Query(default=None),
    fee_stage: str | None = Query(default=None),
    query: str | None = Query(default=None),
    is_enabled: bool | None = Query(default=None),
):
    return FeeItemDefinitionService(db).list_items(
        business_type=business_type,
        fee_stage=fee_stage,
        query=query,
        is_enabled=is_enabled,
    )


@router.post("", response_model=FeeItemDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_fee_item(
    payload: FeeItemDefinitionCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return FeeItemDefinitionService(db).create_item(payload)


@router.put("/{item_id}", response_model=FeeItemDefinitionRead)
def update_fee_item(
    item_id: int,
    payload: FeeItemDefinitionCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = FeeItemDefinitionService(db).update_item(item_id, payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Fee item not found")
    return item


@router.patch("/{item_id}/enabled", response_model=FeeItemDefinitionRead)
def update_fee_item_enabled(
    item_id: int,
    payload: FeeItemEnabledUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = FeeItemDefinitionService(db).set_enabled(item_id, payload.is_enabled)
    if item is None:
        raise HTTPException(status_code=404, detail="Fee item not found")
    return item
