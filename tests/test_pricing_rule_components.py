from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import FeeComponentDefinition, PricingRule
from app.schemas.pricing_rule import PricingRuleComponentCreate
from app.services.pricing_rule_components import PricingRuleComponentService


def test_active_pricing_rule_component_periods_cannot_overlap():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add(
            PricingRule(
                id=1,
                country_region="美国",
                patent_type="发明",
                filing_route="巴黎公约",
                entity_type=None,
                fee_stage="申请阶段",
                fee_item="新申请基础费",
                currency="USD",
                effective_date=date(2026, 1, 1),
                status="active",
            )
        )
        db.add(
            FeeComponentDefinition(
                id=1,
                component_code="US_OFFICIAL_BASIC",
                component_name="官费基础费",
                component_type="official_fee",
                default_currency="USD",
                display_order=100,
                is_enabled=True,
            )
        )
        db.commit()

        service = PricingRuleComponentService(db)
        service.create_component(
            PricingRuleComponentCreate(
                rule_id=1,
                component_code="US_OFFICIAL_BASIC",
                component_type="official_fee",
                currency="USD",
                amount_formula="320",
                effective_date=date(2026, 1, 1),
                expiry_date=date(2026, 6, 30),
                status="enabled",
            )
        )

        with pytest.raises(ValueError, match="生效区间不得重叠"):
            service.create_component(
                PricingRuleComponentCreate(
                    rule_id=1,
                    component_code="US_OFFICIAL_BASIC",
                    component_type="official_fee",
                    currency="USD",
                    amount_formula="350",
                    effective_date=date(2026, 6, 1),
                    expiry_date=None,
                    status="enabled",
                )
            )


def test_pricing_rule_component_requires_amount_formula_and_unique_effective_date():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add(
            PricingRule(
                id=1,
                country_region="美国",
                patent_type="发明",
                filing_route="巴黎公约",
                entity_type=None,
                fee_stage="申请阶段",
                fee_item="新申请基础费",
                currency="USD",
                effective_date=date(2026, 1, 1),
                status="active",
            )
        )
        db.add(
            FeeComponentDefinition(
                id=1,
                component_code="US_OFFICIAL_BASIC",
                component_name="官费基础费",
                component_type="official_fee",
                default_currency="USD",
                display_order=100,
                is_enabled=True,
            )
        )
        db.commit()

        service = PricingRuleComponentService(db)
        service.create_component(
            PricingRuleComponentCreate(
                rule_id=1,
                component_code="US_OFFICIAL_BASIC",
                component_type="official_fee",
                currency="USD",
                amount_formula="320",
                effective_date=date(2026, 1, 1),
                status="disabled",
            )
        )

        with pytest.raises(ValueError, match="金额/公式不能为空"):
            service.create_component(
                PricingRuleComponentCreate(
                    rule_id=1,
                    component_code="US_OFFICIAL_BASIC",
                    component_type="official_fee",
                    currency="USD",
                    amount_formula="",
                    effective_date=date(2026, 2, 1),
                    status="enabled",
                )
            )

        with pytest.raises(ValueError, match="生效日期不能重复"):
            service.create_component(
                PricingRuleComponentCreate(
                    rule_id=1,
                    component_code="US_OFFICIAL_BASIC",
                    component_type="official_fee",
                    currency="USD",
                    amount_formula="350",
                    effective_date=date(2026, 1, 1),
                    status="disabled",
                )
            )
