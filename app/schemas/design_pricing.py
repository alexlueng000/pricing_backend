from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import ORMModel, TimestampSchema


class DesignPricingTierBase(BaseModel):
    min_design_count: int
    max_design_count: int | None = None
    total_price: Decimal


class DesignPricingTierRead(DesignPricingTierBase, ORMModel):
    id: int
    config_id: int


class DesignPricingConfigBase(BaseModel):
    country_region: str
    country_aliases: str | None = None
    business_type: str = "design"
    examination_category: str | None = None
    examination_category_label: str | None = None
    base_price: Decimal = Decimal("0.00")
    allow_multiple_designs: bool
    multiple_design_pricing_mode: str
    multiple_design_warning: str | None = None
    status: str = "active"


class DesignPricingConfigCreate(DesignPricingConfigBase):
    pass


class DesignPricingConfigRead(DesignPricingConfigBase, TimestampSchema):
    id: int
    tiers: list[DesignPricingTierRead] = []
