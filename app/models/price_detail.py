from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class PriceDetail(TimestampMixin, Base):
    __tablename__ = "price_details"
    __table_args__ = (
        Index(
            "idx_price_details_lookup",
            "country_region",
            "patent_type",
            "filing_route",
            "entity_type",
            "fee_stage",
            "status",
        ),
        Index("idx_price_details_display", "display_category", "fee_type"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    country_region: Mapped[str] = mapped_column(String(100), nullable=False)
    patent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    fee_group_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fee_group_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    component_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    component_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filing_route: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fee_stage: Mapped[str] = mapped_column(String(100), nullable=False)
    display_category: Mapped[str] = mapped_column(String(255), nullable=False)
    display_section: Mapped[str | None] = mapped_column(String(50), nullable=True)
    display_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    fee_type: Mapped[str] = mapped_column(String(50), nullable=False)
    fee_sub_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payee_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payee_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payee_country: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_pass_through: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_formula: Mapped[str] = mapped_column(Text, nullable=False)
    is_tax_included: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    official_fee_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    official_fee_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
