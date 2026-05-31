from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import ExchangeRate, PricingRule, Quote, QuoteInput
from app.services.quotes import QuoteService


def test_calculate_quote_generates_fee_items_and_total():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        quote = Quote(
            id=1,
            quote_no="Q20260530000001",
            consultant_id=1,
            customer_name="测试客户",
            status="draft",
            quote_date=date(2026, 5, 30),
            valid_until=date(2026, 6, 14),
            country_region="美国",
            patent_type="发明",
            filing_route="巴黎公约",
            total_cny=Decimal("0.00"),
            is_estimate=True,
            requires_china_invoice=True,
            invoice_tax_rate=Decimal("0.0672"),
        )
        quote.inputs = [
            QuoteInput(
                id=1,
                field_key="entity_type",
                field_label="实体类型",
                field_value="大实体",
            ),
            QuoteInput(
                id=2,
                field_key="claims_count",
                field_label="权利要求项数",
                field_value="24",
            ),
        ]
        db.add(quote)
        db.add(
            PricingRule(
                id=1,
                country_region="美国",
                patent_type="发明",
                filing_route="巴黎公约",
                entity_type="大实体",
                fee_stage="申请阶段",
                fee_item="新申请基础费",
                currency="USD",
                official_fee_formula="320",
                foreign_agent_fee_formula="1200 + max(claims_count - 20, 0) * 80",
                local_agent_fee_formula="5000",
                invoice_tax_policy="add_tax_if_invoice",
                condition_expression="entity_type == '大实体'",
                customer_remark="含基础提交服务。",
                effective_date=date(2026, 1, 1),
                status="active",
            )
        )
        db.add(
            ExchangeRate(
                id=1,
                rate_date=date(2026, 5, 30),
                currency="USD",
                bank_rate=Decimal("7.100000"),
                buffer_type="absolute",
                buffer_value=Decimal("0.100000"),
                final_rate=Decimal("7.200000"),
                source="BOC",
            )
        )
        db.commit()

        calculated = QuoteService(db).calculate_quote(1)

    assert calculated is not None
    assert calculated.status == "generated"
    assert calculated.total_cny == Decimal("19138.27")
    assert len(calculated.fee_items) == 1
    assert calculated.fee_items[0].official_fee == Decimal("320.00")
    assert calculated.fee_items[0].foreign_agent_fee == Decimal("1520.00")
    assert calculated.fee_items[0].local_agent_fee_cny == Decimal("5000.00")
    assert calculated.fee_items[0].tax_cny == Decimal("890.27")
    assert calculated.fee_items[0].subtotal_cny == Decimal("19138.27")


def test_calculate_quote_matches_rules_for_multiple_countries():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        quote = Quote(
            id=1,
            quote_no="Q20260530000002",
            consultant_id=1,
            customer_name="多国客户",
            status="draft",
            quote_date=date(2026, 5, 30),
            valid_until=date(2026, 6, 14),
            country_region="美国、欧洲",
            patent_type="发明",
            filing_route="巴黎公约",
            total_cny=Decimal("0.00"),
            is_estimate=True,
        )
        quote.inputs = [
            QuoteInput(
                id=1,
                field_key="entity_type",
                field_label="实体类型",
                field_value="大实体",
            ),
        ]
        db.add(quote)
        db.add_all(
            [
                PricingRule(
                    id=1,
                    country_region="美国",
                    patent_type="发明",
                    filing_route="巴黎公约",
                    entity_type="大实体",
                    fee_stage="申请阶段",
                    fee_item="美国申请费",
                    currency="USD",
                    official_fee_formula="100",
                    foreign_agent_fee_formula="0",
                    local_agent_fee_formula="1000",
                    effective_date=date(2026, 1, 1),
                    status="active",
                ),
                PricingRule(
                    id=2,
                    country_region="欧洲",
                    patent_type="发明",
                    filing_route="巴黎公约",
                    entity_type="大实体",
                    fee_stage="申请阶段",
                    fee_item="欧洲申请费",
                    currency="EUR",
                    official_fee_formula="200",
                    foreign_agent_fee_formula="0",
                    local_agent_fee_formula="2000",
                    effective_date=date(2026, 1, 1),
                    status="active",
                ),
            ]
        )
        db.add_all(
            [
                ExchangeRate(
                    id=1,
                    rate_date=date(2026, 5, 30),
                    currency="USD",
                    bank_rate=Decimal("7.000000"),
                    buffer_type="absolute",
                    buffer_value=Decimal("0.000000"),
                    final_rate=Decimal("7.000000"),
                    source="BOC",
                ),
                ExchangeRate(
                    id=2,
                    rate_date=date(2026, 5, 30),
                    currency="EUR",
                    bank_rate=Decimal("8.000000"),
                    buffer_type="absolute",
                    buffer_value=Decimal("0.000000"),
                    final_rate=Decimal("8.000000"),
                    source="BOC",
                ),
            ]
        )
        db.commit()

        calculated = QuoteService(db).calculate_quote(1)

    assert calculated is not None
    assert calculated.total_cny == Decimal("5300.00")
    assert [item.fee_item for item in calculated.fee_items] == [
        "美国 - 美国申请费",
        "欧洲 - 欧洲申请费",
    ]


def test_calculate_quote_marks_utility_model_inapplicable_for_us_and_europe():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        quote = Quote(
            id=1,
            quote_no="Q20260530000003",
            consultant_id=1,
            customer_name="实用新型客户",
            status="draft",
            quote_date=date(2026, 5, 30),
            valid_until=date(2026, 6, 14),
            country_region="美国、欧洲、日本、韩国",
            patent_type="实用新型",
            filing_route="巴黎公约",
            total_cny=Decimal("0.00"),
            is_estimate=True,
        )
        quote.inputs = [
            QuoteInput(
                id=1,
                field_key="entity_type",
                field_label="实体类型",
                field_value="大实体",
            ),
        ]
        db.add(quote)
        db.add_all(
            [
                PricingRule(
                    id=1,
                    country_region="日本",
                    patent_type="实用新型",
                    filing_route="巴黎公约",
                    entity_type="大实体",
                    fee_stage="申请阶段",
                    fee_item="日本实用新型申请费",
                    currency="JPY",
                    official_fee_formula="10000",
                    foreign_agent_fee_formula="0",
                    local_agent_fee_formula="1000",
                    effective_date=date(2026, 1, 1),
                    status="active",
                ),
                PricingRule(
                    id=2,
                    country_region="韩国",
                    patent_type="实用新型",
                    filing_route="巴黎公约",
                    entity_type="大实体",
                    fee_stage="申请阶段",
                    fee_item="韩国实用新型申请费",
                    currency="KRW",
                    official_fee_formula="200000",
                    foreign_agent_fee_formula="0",
                    local_agent_fee_formula="2000",
                    effective_date=date(2026, 1, 1),
                    status="active",
                ),
            ]
        )
        db.add_all(
            [
                ExchangeRate(
                    id=1,
                    rate_date=date(2026, 5, 30),
                    currency="JPY",
                    bank_rate=Decimal("0.050000"),
                    buffer_type="absolute",
                    buffer_value=Decimal("0.000000"),
                    final_rate=Decimal("0.050000"),
                    source="BOC",
                ),
                ExchangeRate(
                    id=2,
                    rate_date=date(2026, 5, 30),
                    currency="KRW",
                    bank_rate=Decimal("0.005000"),
                    buffer_type="absolute",
                    buffer_value=Decimal("0.000000"),
                    final_rate=Decimal("0.005000"),
                    source="BOC",
                ),
            ]
        )
        db.commit()

        calculated = QuoteService(db).calculate_quote(1)

    assert calculated is not None
    assert calculated.total_cny == Decimal("4500.00")
    assert [item.fee_item for item in calculated.fee_items] == [
        "美国 - 实用新型不可申请/不适用",
        "欧洲 - 实用新型不可申请/不适用",
        "日本 - 日本实用新型申请费",
        "韩国 - 韩国实用新型申请费",
    ]
    assert calculated.fee_items[0].currency == "N/A"
    assert calculated.fee_items[0].subtotal_cny == Decimal("0.00")
    assert "无实用新型" in (calculated.fee_items[0].remark or "")
