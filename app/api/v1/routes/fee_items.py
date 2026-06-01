from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.fee_item import (
    FeeComponentDefinitionCreate,
    FeeComponentDefinitionRead,
    FeeItemDefinitionCreate,
    FeeItemDefinitionRead,
)
from app.services.fee_items import FeeItemDefinitionService

router = APIRouter(prefix="/fee-items", tags=["fee-items"])


class FeeItemEnabledUpdate(BaseModel):
    is_enabled: bool


class FeeComponentEnabledUpdate(BaseModel):
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


@router.get("/components", response_model=list[FeeComponentDefinitionRead])
def list_fee_components(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    component_type: str | None = Query(default=None),
    query: str | None = Query(default=None),
    is_enabled: bool | None = Query(default=None),
):
    return FeeItemDefinitionService(db).list_components(
        component_type=component_type,
        query=query,
        is_enabled=is_enabled,
    )


@router.post("", response_model=FeeItemDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_fee_item(
    payload: FeeItemDefinitionCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return FeeItemDefinitionService(db).create_item(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/components", response_model=FeeComponentDefinitionRead, status_code=status.HTTP_201_CREATED)
def create_fee_component(
    payload: FeeComponentDefinitionCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return FeeItemDefinitionService(db).create_component(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/components/{component_id}", response_model=FeeComponentDefinitionRead)
def update_fee_component(
    component_id: int,
    payload: FeeComponentDefinitionCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        component = FeeItemDefinitionService(db).update_component(component_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if component is None:
        raise HTTPException(status_code=404, detail="Fee component not found")
    return component


@router.patch("/components/{component_id}/enabled", response_model=FeeComponentDefinitionRead)
def update_fee_component_enabled(
    component_id: int,
    payload: FeeComponentEnabledUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    component = FeeItemDefinitionService(db).set_component_enabled(component_id, payload.is_enabled)
    if component is None:
        raise HTTPException(status_code=404, detail="Fee component not found")
    return component


@router.put("/{item_id}", response_model=FeeItemDefinitionRead)
def update_fee_item(
    item_id: int,
    payload: FeeItemDefinitionCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        item = FeeItemDefinitionService(db).update_item(item_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
