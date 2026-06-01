from sqlalchemy import BigInteger, Boolean, CheckConstraint, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class FeeItemDefinition(TimestampMixin, Base):
    __tablename__ = "fee_items"
    __table_args__ = (
        Index("idx_fee_items_lookup", "business_type", "fee_stage", "is_enabled"),
        Index("idx_fee_items_name", "fee_item_name"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    fee_item_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    fee_item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_type: Mapped[str] = mapped_column(String(100), nullable=False)
    fee_stage: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_basis_type: Mapped[str] = mapped_column(String(50), nullable=False)
    billing_basis_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    pricing_rules: Mapped[list["PricingRule"]] = relationship(back_populates="fee_item_definition")


class FeeComponentDefinition(TimestampMixin, Base):
    __tablename__ = "fee_components"
    __table_args__ = (
        CheckConstraint(
            "component_type IN ('official_fee', 'foreign_agent_fee', 'local_agent_fee')",
            name="ck_fee_components_component_type",
        ),
        Index("idx_fee_components_type", "component_type", "is_enabled"),
        Index("idx_fee_components_name", "component_name"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    component_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    component_name: Mapped[str] = mapped_column(String(255), nullable=False)
    component_type: Mapped[str] = mapped_column(String(50), nullable=False)
    default_currency: Mapped[str] = mapped_column(String(20), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    pricing_rule_components: Mapped[list["PricingRuleComponent"]] = relationship(
        back_populates="component_definition",
    )
