from pydantic import BaseModel

from app.schemas.common import TimestampSchema


class FeeItemDefinitionBase(BaseModel):
    fee_item_code: str
    fee_item_name: str
    business_type: str
    fee_stage: str
    billing_basis_type: str
    display_name_template: str | None = None
    billing_basis_template: str | None = None
    display_order: int
    is_enabled: bool = True
    remark: str | None = None


class FeeItemDefinitionCreate(FeeItemDefinitionBase):
    pass


class FeeItemDefinitionRead(FeeItemDefinitionBase, TimestampSchema):
    id: int
