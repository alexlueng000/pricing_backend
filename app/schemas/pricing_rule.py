from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import TimestampSchema


class PricingRuleComponentBase(BaseModel):
    rule_id: int
    component_code: str
    component_type: str
    currency: str
    amount_formula: str | None = None
    condition_expression: str | None = None
    effective_date: date
    expiry_date: date | None = None
    status: str = "enabled"
    source_reference: str | None = None
    source_attachment: str | None = None
    change_reason: str | None = None
    created_by: int | None = None
    updated_by: int | None = None


class PricingRuleComponentCreate(PricingRuleComponentBase):
    pass


class PricingRuleComponentRead(PricingRuleComponentBase, TimestampSchema):
    id: int


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
    components: list[PricingRuleComponentRead] = Field(default_factory=list)


class PricingRuleImportResponse(BaseModel):
    filename: str
    message: str
    imported_count: int = 0
    skipped_count: int = 0
