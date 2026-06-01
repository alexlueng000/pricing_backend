from pydantic import BaseModel

from app.schemas.common import TimestampSchema


class FeeComponentDefinitionBase(BaseModel):
    component_code: str
    component_name: str
    component_type: str
    default_currency: str
    display_order: int
    is_enabled: bool = True
    remark: str | None = None


class FeeComponentDefinitionCreate(FeeComponentDefinitionBase):
    pass


class FeeComponentDefinitionRead(FeeComponentDefinitionBase, TimestampSchema):
    id: int


class FeeItemDefinitionBase(BaseModel):
    fee_item_code: str
    fee_item_name: str
    business_type: str
    fee_stage: str
    billing_basis_type: str
    billing_basis_template: str | None = None
    display_order: int
    is_enabled: bool = True
    remark: str | None = None


class FeeItemDefinitionCreate(FeeItemDefinitionBase):
    pass


class FeeItemDefinitionRead(FeeItemDefinitionBase, TimestampSchema):
    id: int
