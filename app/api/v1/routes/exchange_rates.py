from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.exchange_rate import ExchangeRateCreate, ExchangeRateRead
from app.services.exchange_rates import ExchangeRateService

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.get("", response_model=list[ExchangeRateRead])
def list_exchange_rates(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    currency: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
):
    return ExchangeRateService(db).list_latest(
        currency=currency,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("", response_model=ExchangeRateRead, status_code=status.HTTP_201_CREATED)
def create_exchange_rate(
    payload: ExchangeRateCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return ExchangeRateService(db).create_rate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
