from datetime import date

from pydantic import BaseModel

from app.schemas.common import TimestampSchema


class PriceDetailBase(BaseModel):
    country_region: str
    patent_type: str
    fee_group_id: str | None = None
    fee_group_name: str | None = None
    component_id: str | None = None
    component_name: str | None = None
    filing_route: str | None = None
    entity_type: str | None = None
    fee_stage: str
    display_category: str
    display_section: str | None = None
    display_remark: str | None = None
    condition_expression: str | None = None
    fee_type: str
    fee_sub_type: str | None = None
    payee_type: str | None = None
    payee_name: str | None = None
    payee_country: str | None = None
    is_pass_through: bool | None = None
    currency: str
    amount_formula: str
    is_tax_included: bool = True
    official_fee_code: str | None = None
    official_fee_name: str | None = None
    status: str = "active"
    effective_date: date
    expiry_date: date | None = None
    display_order: int = 100


class PriceDetailCreate(PriceDetailBase):
    pass


class PriceDetailRead(PriceDetailBase, TimestampSchema):
    id: int
