from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.pricing_rule import PricingRule
    from app.models.user import User

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Quote(TimestampMixin, Base):
    __tablename__ = "quotes"
    __table_args__ = (
        Index("idx_quotes_consultant_date", "consultant_id", "quote_date"),
        Index("idx_quotes_customer", "customer_name"),
        Index("idx_quotes_country", "country_region"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    quote_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    consultant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    country_region: Mapped[str] = mapped_column(String(100), nullable=False)
    patent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    filing_route: Mapped[str] = mapped_column(String(100), nullable=False)
    total_cny: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_china_invoice: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    invoice_tax_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.0672"), nullable=False)
    special_tax_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    special_tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    special_tax_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    special_tax_status: Mapped[str] = mapped_column(String(30), default="not_requested", nullable=False)
    special_tax_approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    special_tax_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    special_tax_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_data_version_refs: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_data_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    consultant: Mapped["User"] = relationship(
        back_populates="quotes",
        foreign_keys=[consultant_id],
    )
    inputs: Mapped[list["QuoteInput"]] = relationship(
        back_populates="quote",
        cascade="all, delete-orphan",
    )
    fee_items: Mapped[list["QuoteFeeItem"]] = relationship(
        back_populates="quote",
        cascade="all, delete-orphan",
    )
    exports: Mapped[list["QuoteExport"]] = relationship(
        back_populates="quote",
        cascade="all, delete-orphan",
    )


class QuoteInput(Base):
    __tablename__ = "quote_inputs"
    __table_args__ = (Index("idx_quote_inputs_quote", "quote_id"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), nullable=False)
    field_key: Mapped[str] = mapped_column(String(100), nullable=False)
    field_label: Mapped[str] = mapped_column(String(255), nullable=False)
    field_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    quote: Mapped[Quote] = relationship(back_populates="inputs")


class QuoteFeeItem(Base):
    __tablename__ = "quote_fee_items"
    __table_args__ = (Index("idx_quote_fee_items_quote", "quote_id"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), nullable=False)
    pricing_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("pricing_rules.id"),
        nullable=True,
    )
    fee_stage: Mapped[str] = mapped_column(String(100), nullable=False)
    fee_item_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fee_item: Mapped[str] = mapped_column(String(255), nullable=False)
    fee_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fee_sub_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    display_section: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payee_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payee_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payee_country: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_pass_through: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    billing_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    official_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    foreign_agent_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    local_agent_fee_cny: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    disbursement_fee_cny: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    tax_cny: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    subtotal_cny: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    quote: Mapped[Quote] = relationship(back_populates="fee_items")
    pricing_rule: Mapped["PricingRule | None"] = relationship(back_populates="quote_fee_items")


class QuoteExport(Base):
    __tablename__ = "quote_exports"
    __table_args__ = (Index("idx_quote_exports_quote", "quote_id"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), nullable=False)
    export_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    exported_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    quote: Mapped[Quote] = relationship(back_populates="exports")
    exporter: Mapped["User"] = relationship(back_populates="exports")
