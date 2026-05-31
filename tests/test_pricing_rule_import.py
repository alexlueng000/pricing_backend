from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import PricingRule
from app.services.pricing_rules import PricingRuleService


def test_import_rules_from_csv_with_chinese_headers():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    content = (
        "国家/地区,专利类型,申请路径,实体类型,费用阶段,费用项目,币种,官费公式,"
        "外代费公式,本所代理费公式,条件表达式,客户备注,生效日期\n"
        "美国,发明,巴黎公约,大实体,申请阶段,新申请基础费,USD,320,1200,5000,"
        "entity_type == '大实体',含基础提交服务。,2026-01-01\n"
    ).encode("utf-8-sig")

    with Session(engine) as db:
        imported_count, skipped_count = PricingRuleService(db).import_rules(
            filename="rules.csv",
            content=content,
        )
        rule = db.scalar(select(PricingRule))

    assert imported_count == 1
    assert skipped_count == 0
    assert rule is not None
    assert rule.country_region == "美国"
    assert rule.official_fee_formula == "320"
    assert rule.condition_expression == "entity_type == '大实体'"
