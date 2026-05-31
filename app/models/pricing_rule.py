from datetime import date

from sqlalchemy import BigInteger, Date, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class PricingRule(TimestampMixin, Base):
    __tablename__ = "pricing_rules"
    __table_args__ = (
        Index(
            "idx_pricing_rules_lookup",
            "country_region",
            "patent_type",
            "filing_route",
            "entity_type",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    country_region: Mapped[str] = mapped_column(String(100), nullable=False)
    patent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    filing_route: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fee_stage: Mapped[str] = mapped_column(String(100), nullable=False)
    fee_item: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    official_fee_formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    foreign_agent_fee_formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_agent_fee_formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_tax_policy: Mapped[str] = mapped_column(String(50), default="tax_included", nullable=False)
    condition_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)

    quote_fee_items: Mapped[list["QuoteFeeItem"]] = relationship(
        back_populates="pricing_rule",
    )
