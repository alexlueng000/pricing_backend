from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.config import (
    ConfigDictionaryCreate,
    ConfigDictionaryRead,
    CountryConfigCreate,
    CountryConfigRead,
)
from app.services.config import ConfigService

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/dictionaries", response_model=list[ConfigDictionaryRead])
def list_dictionaries(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    dict_type: str | None = Query(default=None),
    is_enabled: bool | None = Query(default=None),
):
    return ConfigService(db).list_dictionaries(dict_type=dict_type, is_enabled=is_enabled)


@router.post("/dictionaries", response_model=ConfigDictionaryRead, status_code=status.HTTP_201_CREATED)
def create_dictionary(
    payload: ConfigDictionaryCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ConfigService(db).create_dictionary(payload)


@router.put("/dictionaries/{item_id}", response_model=ConfigDictionaryRead)
def update_dictionary(
    item_id: int,
    payload: ConfigDictionaryCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = ConfigService(db).update_dictionary(item_id, payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Dictionary item not found")
    return item


@router.get("/countries", response_model=list[CountryConfigRead])
def list_countries(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    is_enabled: bool | None = Query(default=None),
):
    return ConfigService(db).list_countries(is_enabled=is_enabled)


@router.post("/countries", response_model=CountryConfigRead, status_code=status.HTTP_201_CREATED)
def create_country(
    payload: CountryConfigCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return ConfigService(db).create_country(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/countries/{item_id}", response_model=CountryConfigRead)
def update_country(
    item_id: int,
    payload: CountryConfigCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        item = ConfigService(db).update_country(item_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Country config not found")
    return item
