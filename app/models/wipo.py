from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class WipoDataSource(TimestampMixin, Base):
    __tablename__ = "wipo_data_sources"
    __table_args__ = (
        UniqueConstraint("source_code", name="uk_wipo_data_sources_code"),
        Index("idx_wipo_data_sources_status", "last_checked_at", "check_status"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_code: Mapped[str] = mapped_column(String(100), nullable=False)
    source_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    official_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="wipo_official", nullable=False)
    current_version: Mapped[str] = mapped_column(String(50), default="V0", nullable=False)
    current_version_id: Mapped[int | None] = mapped_column(ForeignKey("wipo_source_versions.id"), nullable=True)
    source_status_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_status_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_status: Mapped[str] = mapped_column(String(50), default="never_checked", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    histories: Mapped[list["WipoDataSourceHistory"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
    )


class WipoSourceVersion(Base):
    __tablename__ = "wipo_source_versions"
    __table_args__ = (
        UniqueConstraint("source_id", "version_no", name="uk_wipo_source_versions_source_version"),
        Index("idx_wipo_source_versions_source", "source_id", "published_at"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("wipo_data_sources.id"), nullable=False)
    version_no: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_status_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    raw_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    source: Mapped[WipoDataSource] = relationship(foreign_keys=[source_id])
    publisher: Mapped["User | None"] = relationship(foreign_keys=[published_by])


class WipoDataSourceHistory(Base):
    __tablename__ = "wipo_data_source_histories"
    __table_args__ = (Index("idx_wipo_source_histories_source", "source_id", "created_at"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("wipo_data_sources.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    source_status_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="checked", nullable=False)
    operated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    source: Mapped[WipoDataSource] = relationship(back_populates="histories")
    operator: Mapped["User | None"] = relationship()


class WipoDetectionResult(Base):
    __tablename__ = "wipo_detection_results"
    __table_args__ = (
        Index("idx_wipo_detection_results_source", "source_id", "detected_at"),
        Index("idx_wipo_detection_results_status", "status", "published_at"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("wipo_data_sources.id"), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_status_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    parsed_record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    validation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    source: Mapped[WipoDataSource] = relationship()
    publisher: Mapped["User | None"] = relationship(foreign_keys=[published_by])
    creator: Mapped["User | None"] = relationship(foreign_keys=[created_by])


class WipoCountryTreatyStatus(TimestampMixin, Base):
    __tablename__ = "wipo_country_treaty_statuses"
    __table_args__ = (
        UniqueConstraint("country_code", name="uk_wipo_country_treaty_statuses_code"),
        Index("idx_wipo_country_treaty_statuses_lookup", "country_code", "is_pct_member", "is_paris_member"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    country_code: Mapped[str] = mapped_column(String(50), nullable=False)
    name_zh: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_pct_member: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_paris_member: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_wto_member: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_status_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="V0", nullable=False)


class WipoBaseEntity(TimestampMixin, Base):
    __tablename__ = "wipo_base_entities"
    __table_args__ = (
        UniqueConstraint("code", name="uk_wipo_base_entities_code"),
        Index("idx_wipo_base_entities_type", "data_type", "is_active"),
        Index("idx_wipo_base_entities_membership", "is_pct_member", "is_paris_member", "is_wto_member"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name_zh: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_pct_member: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_paris_member: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_wto_member: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pct_entry_deadline_chapter_1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_version_id: Mapped[int | None] = mapped_column(ForeignKey("wipo_source_versions.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    source_version: Mapped["WipoSourceVersion | None"] = relationship()


class WipoPctTimeLimit(TimestampMixin, Base):
    __tablename__ = "wipo_pct_time_limits"
    __table_args__ = (
        UniqueConstraint("country_code", name="uk_wipo_pct_time_limits_country"),
        Index("idx_wipo_pct_time_limits_country", "country_code"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    country_code: Mapped[str] = mapped_column(String(50), nullable=False)
    pct_entry_deadline_first_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_status_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="V0", nullable=False)
