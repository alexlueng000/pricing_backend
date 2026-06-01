import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.schemas.fee_item import FeeComponentDefinitionCreate, FeeItemDefinitionCreate
from app.services.fee_items import FeeItemDefinitionService


def test_fee_item_requires_key_fields_and_unique_code():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        service = FeeItemDefinitionService(db)

        with pytest.raises(ValueError, match="费用项编码不能为空"):
            service.create_item(
                FeeItemDefinitionCreate(
                    fee_item_code="",
                    fee_item_name="新申请基础费",
                    business_type="发明",
                    fee_stage="申请阶段",
                    billing_basis_type="fixed",
                    display_order=100,
                )
            )

        service.create_item(
            FeeItemDefinitionCreate(
                fee_item_code="US_INVENTION_FILING",
                fee_item_name="新申请基础费",
                business_type="发明",
                fee_stage="申请阶段",
                billing_basis_type="fixed",
                display_order=100,
            )
        )

        with pytest.raises(ValueError, match="费用项编码已存在"):
            service.create_item(
                FeeItemDefinitionCreate(
                    fee_item_code="US_INVENTION_FILING",
                    fee_item_name="重复费用项",
                    business_type="发明",
                    fee_stage="申请阶段",
                    billing_basis_type="fixed",
                    display_order=200,
                )
            )


def test_fee_item_code_must_use_uppercase_digits_and_underscore_not_starting_digit():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        service = FeeItemDefinitionService(db)

        with pytest.raises(ValueError, match="费用项编码格式错误"):
            service.create_item(
                FeeItemDefinitionCreate(
                    fee_item_code="1",
                    fee_item_name="官方申请费",
                    business_type="发明",
                    fee_stage="申请阶段",
                    billing_basis_type="fixed",
                    display_order=100,
                    is_enabled=True,
                )
            )

        item = service.create_item(
            FeeItemDefinitionCreate(
                fee_item_code="OFFICIAL_APPLICATION_FEE",
                fee_item_name="官方申请费",
                business_type="发明",
                fee_stage="申请阶段",
                billing_basis_type="fixed",
                display_order=100,
                is_enabled=True,
            )
        )

    assert item.fee_item_code == "OFFICIAL_APPLICATION_FEE"
    assert item.fee_item_name == "官方申请费"


def test_fee_component_requires_valid_type_and_unique_code():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        service = FeeItemDefinitionService(db)

        with pytest.raises(ValueError, match="component_type"):
            service.create_component(
                FeeComponentDefinitionCreate(
                    component_code="BAD_TYPE",
                    component_name="错误类型",
                    component_type="bad",
                    default_currency="USD",
                    display_order=100,
                )
            )

        service.create_component(
            FeeComponentDefinitionCreate(
                component_code="US_OFFICIAL_BASIC",
                component_name="官费基础费",
                component_type="official_fee",
                default_currency="USD",
                display_order=100,
            )
        )

        with pytest.raises(ValueError, match="小项编码不能重复"):
            service.create_component(
                FeeComponentDefinitionCreate(
                    component_code="US_OFFICIAL_BASIC",
                    component_name="重复小项",
                    component_type="official_fee",
                    default_currency="USD",
                    display_order=200,
                )
            )
