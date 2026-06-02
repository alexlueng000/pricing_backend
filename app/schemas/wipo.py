from datetime import date, datetime

from app.schemas.common import ORMModel, TimestampSchema


class WipoDataSourceRead(TimestampSchema):
    id: int
    source_code: str
    source_key: str | None = None
    source_name: str
    official_url: str
    source_url: str | None = None
    source_type: str | None = None
    current_version: str
    current_version_id: int | None = None
    source_status_date: date | None
    last_status_date: date | None = None
    last_checked_at: datetime | None
    last_published_at: datetime | None
    check_status: str
    is_active: bool | None = None
    reminder_level: str
    reminder_label: str


class WipoSourceVersionRead(ORMModel):
    id: int
    source_id: int
    version_no: str
    source_url: str
    source_status_date: date | None
    fetched_at: datetime | None
    published_at: datetime | None
    published_by: int | None
    raw_snapshot: str | None
    parsed_snapshot: str | None
    change_summary: str | None
    created_at: datetime


class WipoDataSourceHistoryRead(ORMModel):
    id: int
    source_id: int
    version: str
    source_status_date: date | None
    checked_at: datetime | None
    published_at: datetime | None
    status: str
    operated_by: int | None
    summary: str | None
    created_at: datetime


class WipoDetectionResultRead(ORMModel):
    id: int
    source_id: int
    detected_at: datetime
    status: str
    failure_reason: str | None
    source_status_date: date | None
    parsed_record_count: int
    validation_summary: str | None
    raw_snapshot: str | None
    parsed_payload: str | None
    published_at: datetime | None
    published_by: int | None
    created_by: int | None
    created_at: datetime


class WipoCountryTreatyStatusRead(TimestampSchema):
    id: int
    country_code: str
    name_zh: str
    name_en: str | None
    is_pct_member: bool
    is_paris_member: bool
    is_wto_member: bool
    source_url: str | None
    source_status_date: date | None
    version: str


class WipoBaseEntityRead(TimestampSchema):
    id: int
    code: str
    name_zh: str
    name_en: str | None
    data_type: str
    is_pct_member: bool
    is_paris_member: bool
    is_wto_member: bool
    pct_entry_deadline_chapter_1: int | None
    source_version_id: int | None
    note: str | None
    is_active: bool


class WipoPctTimeLimitRead(TimestampSchema):
    id: int
    country_code: str
    pct_entry_deadline_first_chapter: int
    source_url: str | None
    source_status_date: date | None
    version: str
