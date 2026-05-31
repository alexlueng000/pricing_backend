from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.quote import QuoteCreate, QuoteRead, QuoteUpdateStatus
from app.services.quotes import QuoteService

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post("", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
def create_quote(
    payload: QuoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return QuoteService(db).create_quote(payload, consultant_id=current_user.id)


@router.get("", response_model=list[QuoteRead])
def list_my_quotes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return QuoteService(db).list_consultant_quotes(current_user.id)


@router.get("/{quote_id}", response_model=QuoteRead)
def get_quote(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    quote = QuoteService(db).get_quote(quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote.consultant_id != current_user.id and (
        current_user.role is None or current_user.role.code != "admin"
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    return quote


@router.patch("/{quote_id}/status", response_model=QuoteRead)
def update_quote_status(
    quote_id: int,
    payload: QuoteUpdateStatus,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = QuoteService(db).get_quote(quote_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    if existing.consultant_id != current_user.id and (
        current_user.role is None or current_user.role.code != "admin"
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    try:
        quote = QuoteService(db).update_status(quote_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote


@router.post("/{quote_id}/calculate", response_model=QuoteRead)
def calculate_quote(
    quote_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = QuoteService(db)
    existing = service.get_quote(quote_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    if existing.consultant_id != current_user.id and (
        current_user.role is None or current_user.role.code != "admin"
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    try:
        quote = service.calculate_quote(quote_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote
