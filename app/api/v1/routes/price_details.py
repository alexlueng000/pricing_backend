from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.price_detail import PriceDetailCreate, PriceDetailRead
from app.services.price_details import PriceDetailService

router = APIRouter(prefix="/price-details", tags=["price-details"])


@router.get("", response_model=list[PriceDetailRead])
def list_price_details(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    country_region: str | None = Query(default=None),
    patent_type: str | None = Query(default=None),
    filing_route: str | None = Query(default=None),
    fee_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
):
    return PriceDetailService(db).list_details(
        country_region=country_region,
        patent_type=patent_type,
        filing_route=filing_route,
        fee_type=fee_type,
        status=status_filter,
    )


@router.post("", response_model=PriceDetailRead, status_code=status.HTTP_201_CREATED)
def create_price_detail(
    payload: PriceDetailCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return PriceDetailService(db).create_detail(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{detail_id}", response_model=PriceDetailRead)
def update_price_detail(
    detail_id: int,
    payload: PriceDetailCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        detail = PriceDetailService(db).update_detail(detail_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail="Price detail not found")
    return detail
