from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, TimestampSchema


class QuoteInputBase(BaseModel):
    field_key: str
    field_label: str
    field_value: str | None = None


class QuoteInputCreate(QuoteInputBase):
    pass


class QuoteInputRead(QuoteInputBase, ORMModel):
    id: int
    quote_id: int
    created_at: datetime


class QuoteFeeItemBase(BaseModel):
    fee_stage: str
    fee_item_code: str | None = None
    fee_item: str
    fee_type: str | None = None
    fee_sub_type: str | None = None
    display_section: str | None = None
    payee_type: str | None = None
    payee_name: str | None = None
    payee_country: str | None = None
    is_pass_through: bool | None = None
    billing_basis: str | None = None
    currency: str
    official_fee: Decimal = Decimal("0.00")
    foreign_agent_fee: Decimal = Decimal("0.00")
    local_agent_fee_cny: Decimal = Decimal("0.00")
    disbursement_fee_cny: Decimal = Decimal("0.00")
    tax_cny: Decimal = Decimal("0.00")
    subtotal_cny: Decimal = Decimal("0.00")
    remark: str | None = None


class QuoteFeeItemCreate(QuoteFeeItemBase):
    pricing_rule_id: int | None = None


class QuoteFeeItemRead(QuoteFeeItemBase, ORMModel):
    id: int
    quote_id: int
    pricing_rule_id: int | None = None
    created_at: datetime


class QuoteBase(BaseModel):
    customer_name: str
    quote_date: date
    valid_until: date | None = None
    country_region: str
    patent_type: str
    filing_route: str
    is_estimate: bool = False
    requires_china_invoice: bool = False
    invoice_tax_rate: Decimal = Decimal("0.0672")
    special_tax_required: bool = False
    special_tax_rate: Decimal | None = None
    special_tax_reason: str | None = None
    special_tax_status: str = "not_requested"
    special_tax_approved_by: int | None = None
    special_tax_approved_at: datetime | None = None
    special_tax_remark: str | None = None
    base_data_version_refs: str | None = None
    base_data_snapshot: str | None = None


class QuoteCreate(QuoteBase):
    inputs: list[QuoteInputCreate] = Field(default_factory=list)


class QuoteUpdateStatus(BaseModel):
    status: str


class QuoteRead(QuoteBase, TimestampSchema):
    id: int
    quote_no: str
    consultant_id: int
    status: str
    total_cny: Decimal
    inputs: list[QuoteInputRead] = Field(default_factory=list)
    fee_items: list[QuoteFeeItemRead] = Field(default_factory=list)
