from datetime import date

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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
    fee_item_code: Mapped[str | None] = mapped_column(ForeignKey("fee_items.fee_item_code"), nullable=True)
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
    fee_item_definition: Mapped["FeeItemDefinition | None"] = relationship(back_populates="pricing_rules")
    components: Mapped[list["PricingRuleComponent"]] = relationship(
        back_populates="pricing_rule",
        cascade="all, delete-orphan",
        order_by="PricingRuleComponent.effective_date",
    )


class PricingRuleComponent(TimestampMixin, Base):
    __tablename__ = "pricing_rule_components"
    __table_args__ = (
        UniqueConstraint("rule_id", "component_code", "effective_date", name="uk_rule_component_effective"),
        CheckConstraint(
            "component_type IN ('official_fee', 'foreign_agent_fee', 'local_agent_fee')",
            name="ck_pricing_rule_components_component_type",
        ),
        Index("idx_pricing_rule_components_rule", "rule_id", "status"),
        Index("idx_pricing_rule_components_component", "component_code"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("pricing_rules.id"), nullable=False)
    component_code: Mapped[str] = mapped_column(ForeignKey("fee_components.component_code"), nullable=False)
    component_type: Mapped[str] = mapped_column(String(50), nullable=False)
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_formula: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_attachment: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    pricing_rule: Mapped["PricingRule"] = relationship(back_populates="components")
    component_definition: Mapped["FeeComponentDefinition"] = relationship(
        back_populates="pricing_rule_components",
    )
