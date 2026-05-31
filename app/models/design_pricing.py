from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class DesignPricingConfig(TimestampMixin, Base):
    __tablename__ = "design_pricing_configs"
    __table_args__ = (
        Index(
            "idx_design_pricing_configs_lookup",
            "business_type",
            "country_region",
            "examination_category",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    country_region: Mapped[str] = mapped_column(String(100), nullable=False)
    country_aliases: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_type: Mapped[str] = mapped_column(String(50), nullable=False)
    examination_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    examination_category_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    allow_multiple_designs: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    multiple_design_pricing_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    multiple_design_warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)

    tiers: Mapped[list["DesignPricingTier"]] = relationship(
        back_populates="config",
        cascade="all, delete-orphan",
    )


class DesignPricingTier(Base):
    __tablename__ = "design_pricing_tiers"
    __table_args__ = (Index("idx_design_pricing_tiers_config", "config_id"),)

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    config_id: Mapped[int] = mapped_column(ForeignKey("design_pricing_configs.id"), nullable=False)
    min_design_count: Mapped[int] = mapped_column(Integer, nullable=False)
    max_design_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    config: Mapped[DesignPricingConfig] = relationship(back_populates="tiers")
