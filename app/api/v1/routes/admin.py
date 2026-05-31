from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.quote import QuoteRead
from app.schemas.user import UserAdminCreate, UserRead
from app.services.quotes import QuoteService
from app.services.users import UserService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/quotes", response_model=list[QuoteRead])
def list_all_quotes(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return QuoteService(db).list_all_quotes()


@router.get("/users", response_model=list[UserRead])
def list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return UserService(db).list_users()


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserAdminCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return UserService(db).create_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
