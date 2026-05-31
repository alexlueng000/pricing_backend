from datetime import date

from pydantic import BaseModel

from app.schemas.common import TimestampSchema


class PricingRuleBase(BaseModel):
    country_region: str
    patent_type: str
    filing_route: str
    entity_type: str | None = None
    fee_stage: str
    fee_item_code: str | None = None
    fee_item: str = ""
    currency: str
    official_fee_formula: str | None = None
    foreign_agent_fee_formula: str | None = None
    local_agent_fee_formula: str | None = None
    invoice_tax_policy: str = "tax_included"
    condition_expression: str | None = None
    customer_remark: str | None = None
    internal_note: str | None = None
    effective_date: date
    status: str = "active"


class PricingRuleCreate(PricingRuleBase):
    pass


class PricingRuleRead(PricingRuleBase, TimestampSchema):
    id: int


class PricingRuleImportResponse(BaseModel):
    filename: str
    message: str
    imported_count: int = 0
    skipped_count: int = 0
