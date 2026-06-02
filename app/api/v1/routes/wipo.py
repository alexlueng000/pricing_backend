from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.wipo import (
    WipoBaseEntityRead,
    WipoCountryTreatyStatusRead,
    WipoDataSourceHistoryRead,
    WipoDataSourceRead,
    WipoDetectionResultRead,
    WipoPctTimeLimitRead,
    WipoSourceVersionRead,
)
from app.services.wipo import WipoService

router = APIRouter(prefix="/wipo", tags=["wipo"])


@router.get("/data-sources", response_model=list[WipoDataSourceRead])
def list_wipo_data_sources(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return WipoService(db).list_sources()


@router.post("/data-sources/{source_code}/detect", response_model=WipoDetectionResultRead, status_code=status.HTTP_200_OK)
def detect_wipo_data_source(
    source_code: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        result = WipoService(db).detect_source_with_result(source_code, operated_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="WIPO data source not found")
    return result


@router.post("/data-sources/{source_code}/detections/{detection_id}/publish", response_model=WipoDataSourceRead)
def publish_wipo_detection_result(
    source_code: str,
    detection_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        source = WipoService(db).publish_detection(source_code, detection_id, operated_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if source is None:
        raise HTTPException(status_code=404, detail="WIPO detection result not found")
    return WipoService(db)._source_with_reminder(source)


@router.get("/data-sources/{source_code}/histories", response_model=list[WipoDataSourceHistoryRead])
def list_wipo_data_source_histories(
    source_code: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    histories = WipoService(db).list_source_histories(source_code)
    if histories is None:
        raise HTTPException(status_code=404, detail="WIPO data source not found")
    return histories


@router.get("/data-sources/{source_code}/detections", response_model=list[WipoDetectionResultRead])
def list_wipo_detection_results(
    source_code: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    results = WipoService(db).list_detection_results(source_code)
    if results is None:
        raise HTTPException(status_code=404, detail="WIPO data source not found")
    return results


@router.get("/data-sources/{source_code}/versions", response_model=list[WipoSourceVersionRead])
def list_wipo_source_versions(
    source_code: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    versions = WipoService(db).list_source_versions(source_code)
    if versions is None:
        raise HTTPException(status_code=404, detail="WIPO data source not found")
    return versions


@router.get("/base-entities", response_model=list[WipoBaseEntityRead])
def list_wipo_base_entities(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return WipoService(db).list_base_entities()


@router.get("/country-treaty-statuses", response_model=list[WipoCountryTreatyStatusRead])
def list_wipo_country_treaty_statuses(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return WipoService(db).list_treaty_statuses()


@router.get("/pct-time-limits", response_model=list[WipoPctTimeLimitRead])
def list_wipo_pct_time_limits(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return WipoService(db).list_time_limits()
