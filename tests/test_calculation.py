from decimal import Decimal

import pytest

from app.services.calculation import FormulaError, SafeFormulaEvaluator, money, parse_input_value


def test_evaluate_decimal_formula_with_input_fields():
    evaluator = SafeFormulaEvaluator(
        {
            "claims_count": Decimal("24"),
            "base_claims": Decimal("20"),
            "extra_claim_fee": Decimal("80"),
        }
    )

    assert evaluator.evaluate_decimal(
        "max(claims_count - base_claims, 0) * extra_claim_fee"
    ) == Decimal("320")


def test_evaluate_condition_with_text_and_boolean_fields():
    evaluator = SafeFormulaEvaluator(
        {
            "entity_type": "大实体",
            "is_estimate": True,
        }
    )

    assert evaluator.evaluate_condition("entity_type == '大实体' and is_estimate")
    assert evaluator.evaluate_condition("entity_type == '大实体' AND is_estimate")
    assert evaluator.evaluate_condition("entity_type in ['大实体', '小实体']")
    assert not evaluator.evaluate_condition("entity_type == '小实体'")


def test_parse_percentage_and_money_rounding():
    assert parse_input_value("6%") == Decimal("0.06")
    assert parse_input_value("1,234.50") == Decimal("1234.50")
    assert money(Decimal("12.345")) == Decimal("12.35")


def test_rejects_unsafe_expression():
    evaluator = SafeFormulaEvaluator({})

    with pytest.raises(FormulaError):
        evaluator.evaluate("__import__('os').system('echo unsafe')")
