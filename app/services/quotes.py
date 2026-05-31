import re
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.quote import Quote, QuoteFeeItem, QuoteInput
from app.repositories.exchange_rates import ExchangeRateRepository
from app.repositories.pricing_rules import PricingRuleRepository
from app.repositories.quotes import QuoteFeeItemRepository, QuoteRepository
from app.schemas.quote import QuoteCreate
from app.services.calculation import FormulaError, SafeFormulaEvaluator, money, parse_input_value


QUOTE_STATUSES = {"draft", "generated", "sent_to_customer", "voided"}
CNY_CURRENCIES = {"CNY", "RMB", "人民币"}
INAPPLICABLE_PATENT_TYPES = {
    ("美国", "实用新型"): "美国无实用新型制度，该国家不生成实用新型费用。",
    ("欧洲", "实用新型"): "欧洲无实用新型制度，该地区不生成实用新型费用。",
}


class QuoteService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.quotes = QuoteRepository(db)
        self.fee_items = QuoteFeeItemRepository(db)
        self.pricing_rules = PricingRuleRepository(db)
        self.exchange_rates = ExchangeRateRepository(db)

    def create_quote(self, payload: QuoteCreate, *, consultant_id: int) -> Quote:
        quote = Quote(
            quote_no=self._generate_quote_no(),
            consultant_id=consultant_id,
            customer_name=payload.customer_name,
            status="draft",
            quote_date=payload.quote_date,
            valid_until=payload.valid_until,
            country_region=payload.country_region,
            patent_type=payload.patent_type,
            filing_route=payload.filing_route,
            total_cny=Decimal("0.00"),
            is_estimate=payload.is_estimate,
            requires_china_invoice=payload.requires_china_invoice,
            invoice_tax_rate=payload.invoice_tax_rate,
            special_tax_required=payload.special_tax_required,
            special_tax_rate=payload.special_tax_rate,
            special_tax_reason=payload.special_tax_reason,
            special_tax_status=payload.special_tax_status,
            special_tax_approved_by=payload.special_tax_approved_by,
            special_tax_approved_at=payload.special_tax_approved_at,
            special_tax_remark=payload.special_tax_remark,
        )
        quote.inputs = [
            QuoteInput(
                field_key=item.field_key,
                field_label=item.field_label,
                field_value=item.field_value,
            )
            for item in payload.inputs
        ]
        self.quotes.add(quote)
        self.db.commit()
        self.db.refresh(quote)
        return quote

    def get_quote(self, quote_id: int) -> Quote | None:
        return self.quotes.get_detail(quote_id)

    def list_consultant_quotes(self, consultant_id: int) -> list[Quote]:
        return self.quotes.list_for_consultant(consultant_id)

    def list_all_quotes(self) -> list[Quote]:
        return self.quotes.list_all()

    def update_status(self, quote_id: int, status: str) -> Quote | None:
        if status not in QUOTE_STATUSES:
            raise ValueError("Invalid quote status")
        quote = self.quotes.get(quote_id)
        if quote is None:
            return None
        quote.status = status
        self.db.commit()
        self.db.refresh(quote)
        return quote

    def calculate_quote(self, quote_id: int) -> Quote | None:
        quote = self.quotes.get_detail(quote_id)
        if quote is None:
            return None

        input_map = {item.field_key: item.field_value for item in quote.inputs}
        context = self._build_calculation_context(quote, input_map)
        entity_type = input_map.get("entity_size") or input_map.get("entity_type")
        items: list[QuoteFeeItem] = []
        total_cny = Decimal("0.00")
        for country_region in self._split_country_regions(quote.country_region):
            applicability_remark = self._get_applicability_remark(country_region, quote.patent_type)
            if applicability_remark:
                items.append(
                    QuoteFeeItem(
                        quote_id=quote.id,
                        pricing_rule_id=None,
                        fee_stage="申请阶段",
                        fee_item=f"{country_region} - {quote.patent_type}不可申请/不适用",
                        currency="N/A",
                        official_fee=Decimal("0.00"),
                        foreign_agent_fee=Decimal("0.00"),
                        local_agent_fee_cny=Decimal("0.00"),
                        tax_cny=Decimal("0.00"),
                        subtotal_cny=Decimal("0.00"),
                        remark=applicability_remark,
                    )
                )
                continue

            country_context = {
                **context,
                "country_region": country_region,
            }
            rules = self.pricing_rules.find_active_rules(
                country_region=country_region,
                patent_type=quote.patent_type,
                filing_route=quote.filing_route,
                entity_type=entity_type,
                quote_date=quote.quote_date,
            )
            evaluator = SafeFormulaEvaluator(country_context)

            for rule in rules:
                try:
                    if not evaluator.evaluate_condition(rule.condition_expression):
                        continue
                    official_fee = money(evaluator.evaluate_decimal(rule.official_fee_formula))
                    foreign_agent_fee = money(evaluator.evaluate_decimal(rule.foreign_agent_fee_formula))
                    local_agent_fee_cny = money(evaluator.evaluate_decimal(rule.local_agent_fee_formula))
                except FormulaError as exc:
                    raise ValueError(f"费用规则 {rule.id}（{rule.fee_item}）计算失败：{exc}") from exc

                exchange_rate = self._get_exchange_rate(rule.currency, quote.quote_date)
                foreign_fee_cny = money((official_fee + foreign_agent_fee) * exchange_rate)
                tax_cny = self._calculate_tax(
                    quote=quote,
                    rule_policy=rule.invoice_tax_policy,
                    fee_base_cny=foreign_fee_cny,
                )
                subtotal_cny = money(foreign_fee_cny + local_agent_fee_cny + tax_cny)
                total_cny += subtotal_cny

                items.append(
                    QuoteFeeItem(
                        quote_id=quote.id,
                        pricing_rule_id=rule.id,
                        fee_stage=rule.fee_stage,
                        fee_item=f"{country_region} - {rule.fee_item}",
                        currency=rule.currency,
                        official_fee=official_fee,
                        foreign_agent_fee=foreign_agent_fee,
                        local_agent_fee_cny=local_agent_fee_cny,
                        tax_cny=tax_cny,
                        subtotal_cny=subtotal_cny,
                        remark=self._build_fee_remark(rule.customer_remark, rule.currency, exchange_rate),
                    )
                )

        self.fee_items.replace_for_quote(quote.id, items)
        quote.status = "generated"
        quote.total_cny = money(total_cny)
        self.db.commit()
        refreshed = self.quotes.get_detail(quote.id)
        return refreshed

    def _get_exchange_rate(self, currency: str, quote_date) -> Decimal:
        normalized_currency = currency.upper()
        if normalized_currency in CNY_CURRENCIES:
            return Decimal("1.00")

        rate_record = self.exchange_rates.get_for_currency_on_or_before(
            currency=normalized_currency,
            rate_date=quote_date,
        )
        if rate_record is None:
            raise ValueError(f"缺少 {quote_date} 或之前的 {normalized_currency} 汇率")
        return Decimal(rate_record.final_rate)

    def _calculate_tax(
        self,
        *,
        quote: Quote,
        rule_policy: str,
        fee_base_cny: Decimal,
    ) -> Decimal:
        if not quote.requires_china_invoice:
            return Decimal("0.00")
        if rule_policy != "add_tax_if_invoice":
            return Decimal("0.00")
        return money(fee_base_cny * Decimal(str(quote.invoice_tax_rate)))

    def _build_calculation_context(
        self,
        quote: Quote,
        input_map: dict[str, str | None],
    ) -> dict[str, object]:
        context: dict[str, object] = {
            "country_region": quote.country_region,
            "patent_type": quote.patent_type,
            "filing_route": quote.filing_route,
            "is_estimate": quote.is_estimate,
        }
        for key, value in input_map.items():
            context[key] = parse_input_value(value)
        return context

    @staticmethod
    def _split_country_regions(country_region: str) -> list[str]:
        regions = [
            item.strip()
            for item in re.split(r"[,，、/]+", country_region)
            if item.strip()
        ]
        return regions or [country_region]

    @staticmethod
    def _get_applicability_remark(country_region: str, patent_type: str) -> str | None:
        return INAPPLICABLE_PATENT_TYPES.get((country_region, patent_type))

    @staticmethod
    def _build_fee_remark(
        customer_remark: str | None,
        currency: str,
        exchange_rate: Decimal,
    ) -> str | None:
        rate_remark = None
        if currency.upper() not in CNY_CURRENCIES:
            rate_remark = f"按报价日有效汇率 {currency.upper()}={exchange_rate} 折算人民币。"
        if customer_remark and rate_remark:
            return f"{customer_remark} {rate_remark}"
        return customer_remark or rate_remark

    @staticmethod
    def _generate_quote_no() -> str:
        now = datetime.now(timezone.utc)
        return f"Q{now:%Y%m%d%H%M%S%f}"
