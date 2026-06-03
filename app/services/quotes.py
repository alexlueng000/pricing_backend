import json
import re
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.quote import Quote, QuoteFeeItem, QuoteInput
from app.models.wipo import WipoBaseEntity, WipoDataSource
from app.repositories.exchange_rates import ExchangeRateRepository
from app.repositories.price_details import PriceDetailRepository
from app.repositories.pricing_rules import PricingRuleRepository
from app.repositories.quotes import QuoteFeeItemRepository, QuoteRepository
from app.schemas.quote import QuoteCreate
from app.services.calculation import FormulaError, SafeFormulaEvaluator, money, parse_input_value
from app.services.design_pricing import DesignPricingConfigService


QUOTE_STATUSES = {"draft", "generated", "sent_to_customer", "voided"}
CNY_CURRENCIES = {"CNY", "RMB", "人民币"}
FEE_TYPE_ALIASES = {
    "official_fee": "target_official_fee",
    "foreign_agent_fee": "associate_service_fee",
    "local_agent_fee": "our_service_fee",
}
MAIN_DISPLAY_SECTION = "main_table"
DISBURSEMENT_DISPLAY_SECTION = "disbursement_section"
FEE_TYPE_DISPLAY_SECTIONS = {
    "target_official_fee": MAIN_DISPLAY_SECTION,
    "associate_service_fee": MAIN_DISPLAY_SECTION,
    "our_service_fee": MAIN_DISPLAY_SECTION,
    "third_party_disbursement": DISBURSEMENT_DISPLAY_SECTION,
}
DESIGN_EXAMINATION_CATEGORY_DEFAULT = "default_substantive"
DESIGN_EXAMINATION_CATEGORY_VALUES = {
    "substantive_examination",
    "partial_examination",
    DESIGN_EXAMINATION_CATEGORY_DEFAULT,
}
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
        self.price_details = PriceDetailRepository(db)
        self.exchange_rates = ExchangeRateRepository(db)
        self.design_pricing = DesignPricingConfigService(db)

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
            base_data_version_refs=self._current_base_data_version_refs(),
            base_data_snapshot=self._base_data_snapshot_for_quote(payload.country_region),
        )
        inputs = self._normalize_inputs_for_quote(payload)
        quote.inputs = [
            QuoteInput(
                field_key=item.field_key,
                field_label=item.field_label,
                field_value=item.field_value,
            )
            for item in inputs
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

        input_map = self._input_map_with_defaults(quote)
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
                        fee_item_code=None,
                        fee_item=f"{country_region} - {quote.patent_type}不可申请/不适用",
                        billing_basis=f"{country_region}/{quote.patent_type}",
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
                "entity_type": entity_type,
            }
            design_item = self._calculate_design_config_item(
                quote=quote,
                country_region=country_region,
                input_map=input_map,
            )
            if design_item is not None:
                total_cny += design_item.subtotal_cny
                items.append(design_item)
                continue

            price_detail_items = self._calculate_price_detail_items(
                quote=quote,
                country_region=country_region,
                patent_type=quote.patent_type,
                filing_route=quote.filing_route,
                entity_type=str(entity_type) if entity_type is not None else None,
                context=country_context,
            )
            if price_detail_items:
                total_cny += sum((item.subtotal_cny for item in price_detail_items), Decimal("0.00"))
                items.extend(price_detail_items)
                continue

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
                    official_fee, foreign_agent_fee, local_agent_fee_cny = self._evaluate_rule_amounts(
                        rule,
                        evaluator,
                        quote.quote_date,
                    )
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
                        fee_item_code=rule.fee_item_code,
                        fee_item=self._fee_item_display_name(rule),
                        billing_basis=self._render_billing_basis(rule, country_context),
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

    def _normalize_inputs_for_quote(self, payload: QuoteCreate):
        inputs = list(payload.inputs)
        examination_category = next(
            (item for item in inputs if item.field_key == "examination_category"),
            None,
        )
        if examination_category is None:
            return inputs

        if examination_category.field_value not in DESIGN_EXAMINATION_CATEGORY_VALUES:
            raise ValueError("外观设计审查类别不合法")
        return inputs

    def _input_map_with_defaults(self, quote: Quote) -> dict[str, str | None]:
        input_map = {item.field_key: item.field_value for item in quote.inputs}
        if quote.patent_type == "外观设计":
            input_map.setdefault(
                "examination_category",
                DESIGN_EXAMINATION_CATEGORY_DEFAULT,
            )
        return input_map

    def _calculate_design_config_item(
        self,
        *,
        quote: Quote,
        country_region: str,
        input_map: dict[str, str | None],
    ) -> QuoteFeeItem | None:
        if quote.patent_type != "外观设计":
            return None

        config = self.design_pricing.find_config(
            country_region=country_region,
            business_type="design",
            examination_category=input_map.get("examination_category"),
        )
        if config is None:
            return None

        design_count = self._design_count(input_map)
        total_price = money(
            self.design_pricing.calculate_total_price(
                config=config,
                design_count=design_count,
            )
        )
        remark = None
        if design_count > 1 and config.multiple_design_warning:
            remark = config.multiple_design_warning
        if config.examination_category_label:
            remark = f"{remark} {config.examination_category_label}" if remark else config.examination_category_label

        return QuoteFeeItem(
            quote_id=quote.id,
            pricing_rule_id=None,
            fee_stage="申请阶段",
            fee_item_code=None,
            fee_item=f"{country_region} - 外观设计基础报价",
            billing_basis=f"设计项数：{design_count}项",
            currency="CNY",
            official_fee=Decimal("0.00"),
            foreign_agent_fee=Decimal("0.00"),
            local_agent_fee_cny=total_price,
            tax_cny=Decimal("0.00"),
            subtotal_cny=total_price,
            remark=remark,
        )

    def _calculate_price_detail_items(
        self,
        *,
        quote: Quote,
        country_region: str,
        patent_type: str,
        filing_route: str,
        entity_type: str | None,
        context: dict[str, object],
    ) -> list[QuoteFeeItem]:
        details = self.price_details.find_active_details(
            country_region=country_region,
            patent_type=patent_type,
            filing_route=filing_route,
            entity_type=entity_type,
            quote_date=quote.quote_date,
        )
        if not details:
            return []

        evaluator = SafeFormulaEvaluator(context)
        selected_details = self._select_best_price_details(
            details=details,
            filing_route=filing_route,
            entity_type=entity_type,
        )
        groups: dict[tuple[str, str, str | None, str], dict[str, object]] = {}
        for detail in selected_details:
            try:
                if not evaluator.evaluate_condition(detail.condition_expression):
                    continue
                amount = money(evaluator.evaluate_decimal(detail.amount_formula))
            except FormulaError as exc:
                raise ValueError(f"底层价格 {detail.id}（{detail.display_category}）计算失败：{exc}") from exc

            normalized_fee_type = self._normalize_fee_type(detail.fee_type)
            display_section = detail.display_section or self._default_display_section(normalized_fee_type)
            key = (detail.fee_stage, detail.display_category, detail.display_remark, display_section)
            group = groups.setdefault(
                key,
                {
                    "fee_stage": detail.fee_stage,
                    "display_category": detail.display_category,
                    "display_remark": detail.display_remark,
                    "display_section": display_section,
                    "fee_types": set(),
                    "fee_sub_types": set(),
                    "payee_types": set(),
                    "payee_names": set(),
                    "payee_countries": set(),
                    "is_pass_through": None,
                    "currency": None,
                    "official_fee": Decimal("0.00"),
                    "foreign_agent_fee": Decimal("0.00"),
                    "local_agent_fee_cny": Decimal("0.00"),
                    "disbursement_fee_cny": Decimal("0.00"),
                    "foreign_fee_cny": Decimal("0.00"),
                    "taxable_cny": Decimal("0.00"),
                    "display_order": detail.display_order,
                },
            )
            group["display_order"] = min(int(group["display_order"]), detail.display_order)
            group["fee_types"].add(normalized_fee_type)
            if detail.fee_sub_type:
                group["fee_sub_types"].add(detail.fee_sub_type)
            if detail.payee_type:
                group["payee_types"].add(detail.payee_type)
            if detail.payee_name:
                group["payee_names"].add(detail.payee_name)
            if detail.payee_country:
                group["payee_countries"].add(detail.payee_country)
            if detail.is_pass_through is not None:
                group["is_pass_through"] = detail.is_pass_through

            amount_cny = self._amount_to_cny(detail.currency, amount, quote.quote_date)
            if normalized_fee_type == "our_service_fee":
                group["local_agent_fee_cny"] = money(Decimal(group["local_agent_fee_cny"]) + amount_cny)
            elif normalized_fee_type == "target_official_fee":
                self._set_group_currency(group, detail.currency)
                group["official_fee"] = money(Decimal(group["official_fee"]) + amount)
                group["foreign_fee_cny"] = money(Decimal(group["foreign_fee_cny"]) + amount_cny)
            elif normalized_fee_type == "associate_service_fee":
                self._set_group_currency(group, detail.currency)
                group["foreign_agent_fee"] = money(Decimal(group["foreign_agent_fee"]) + amount)
                group["foreign_fee_cny"] = money(Decimal(group["foreign_fee_cny"]) + amount_cny)
            elif normalized_fee_type == "third_party_disbursement":
                group["disbursement_fee_cny"] = money(Decimal(group["disbursement_fee_cny"]) + amount_cny)

            if not detail.is_tax_included:
                group["taxable_cny"] = money(Decimal(group["taxable_cny"]) + amount_cny)

        items: list[QuoteFeeItem] = []
        for group in sorted(
            groups.values(),
            key=lambda item: (item["fee_stage"], item["display_order"], item["display_category"]),
        ):
            tax_cny = self._calculate_detail_tax(
                quote=quote,
                taxable_cny=Decimal(group["taxable_cny"]),
            )
            subtotal_cny = money(
                Decimal(group["foreign_fee_cny"])
                + Decimal(group["local_agent_fee_cny"])
                + Decimal(group["disbursement_fee_cny"])
                + tax_cny
            )
            items.append(
                QuoteFeeItem(
                    quote_id=quote.id,
                    pricing_rule_id=None,
                    fee_stage=str(group["fee_stage"]),
                    fee_item_code=None,
                    fee_item=str(group["display_category"]),
                    fee_type=self._single_or_none(group["fee_types"]),
                    fee_sub_type=self._single_or_none(group["fee_sub_types"]),
                    display_section=str(group["display_section"]),
                    payee_type=self._single_or_none(group["payee_types"]),
                    payee_name=self._single_or_none(group["payee_names"]),
                    payee_country=self._single_or_none(group["payee_countries"]),
                    is_pass_through=group["is_pass_through"],
                    billing_basis=None,
                    currency=str(group["currency"] or "CNY"),
                    official_fee=Decimal(group["official_fee"]),
                    foreign_agent_fee=Decimal(group["foreign_agent_fee"]),
                    local_agent_fee_cny=Decimal(group["local_agent_fee_cny"]),
                    disbursement_fee_cny=Decimal(group["disbursement_fee_cny"]),
                    tax_cny=tax_cny,
                    subtotal_cny=subtotal_cny,
                    remark=group["display_remark"],
                )
            )
        return items

    @classmethod
    def _select_best_price_details(
        cls,
        *,
        details,
        filing_route: str,
        entity_type: str | None,
    ):
        selected = {}
        for detail in details:
            key = cls._price_detail_identity_key(detail)
            priority = (
                1 if detail.filing_route == filing_route else 0,
                1 if entity_type is not None and detail.entity_type == entity_type else 0,
            )
            current = selected.get(key)
            if current is None or priority > current[0] or (
                priority == current[0] and detail.id > current[1].id
            ):
                selected[key] = (priority, detail)
        return [item[1] for item in selected.values()]

    @classmethod
    def _price_detail_identity_key(cls, detail) -> tuple[object, ...]:
        if detail.fee_group_id or detail.component_id:
            return (
                detail.country_region,
                detail.patent_type,
                detail.fee_stage,
                detail.fee_group_id,
                detail.component_id,
                cls._normalize_fee_type(detail.fee_type),
                detail.fee_sub_type,
                detail.currency,
                detail.condition_expression,
            )
        return (
            detail.country_region,
            detail.patent_type,
            detail.fee_stage,
            detail.display_category,
            detail.display_remark,
            cls._normalize_fee_type(detail.fee_type),
            detail.currency,
            detail.condition_expression,
        )

    @staticmethod
    def _normalize_fee_type(fee_type: str) -> str:
        return FEE_TYPE_ALIASES.get(fee_type, fee_type)

    @staticmethod
    def _default_display_section(fee_type: str) -> str:
        return FEE_TYPE_DISPLAY_SECTIONS.get(fee_type, MAIN_DISPLAY_SECTION)

    @staticmethod
    def _single_or_none(values) -> str | None:
        if not values:
            return None
        if len(values) == 1:
            return next(iter(values))
        return None

    def _amount_to_cny(self, currency: str, amount: Decimal, quote_date) -> Decimal:
        return money(amount * self._get_exchange_rate(currency, quote_date))

    @staticmethod
    def _set_group_currency(group: dict[str, object], currency: str) -> None:
        normalized = currency.upper()
        if normalized in CNY_CURRENCIES:
            return
        current = group.get("currency")
        if current is None:
            group["currency"] = normalized
            return
        if current != normalized:
            raise ValueError("同一展示分类下官费和外所代理费暂不支持混用多个外币币种")

    @staticmethod
    def _calculate_detail_tax(*, quote: Quote, taxable_cny: Decimal) -> Decimal:
        if not quote.requires_china_invoice:
            return Decimal("0.00")
        return money(taxable_cny * Decimal(str(quote.invoice_tax_rate)))

    @staticmethod
    def _evaluate_rule_amounts(rule, evaluator: SafeFormulaEvaluator, quote_date) -> tuple[Decimal, Decimal, Decimal]:
        active_components = [
            component
            for component in rule.components
            if (component.component_definition is None or component.component_definition.is_enabled)
            and component.status in {"enabled", "active"}
            and component.effective_date <= quote_date
            and (component.expiry_date is None or component.expiry_date >= quote_date)
        ]
        if not active_components:
            return (
                money(evaluator.evaluate_decimal(rule.official_fee_formula)),
                money(evaluator.evaluate_decimal(rule.foreign_agent_fee_formula)),
                money(evaluator.evaluate_decimal(rule.local_agent_fee_formula)),
            )

        amounts = {
            "official_fee": Decimal("0.00"),
            "foreign_agent_fee": Decimal("0.00"),
            "local_agent_fee": Decimal("0.00"),
        }
        for component in active_components:
            if not evaluator.evaluate_condition(component.condition_expression):
                continue
            if component.component_definition is None:
                raise FormulaError(f"缺少费用组成定义：{component.component_code}")
            category = component.component_type
            if category not in amounts:
                raise FormulaError(f"未知费用小项类型：{category}")
            amount = money(evaluator.evaluate_decimal(component.amount_formula))
            amounts[category] += amount

        return (
            money(amounts["official_fee"]),
            money(amounts["foreign_agent_fee"]),
            money(amounts["local_agent_fee"]),
        )

    @staticmethod
    def _design_count(input_map: dict[str, str | None]) -> int:
        for field_key in ("design_count", "design_items"):
            value = parse_input_value(input_map.get(field_key))
            try:
                count = int(Decimal(str(value)))
            except Exception:
                continue
            if count > 0:
                return count
        return 1

    @staticmethod
    def _fee_item_display_name(rule) -> str:
        definition = rule.fee_item_definition
        if definition is None:
            return rule.fee_item
        return definition.fee_item_name

    def _render_billing_basis(self, rule, context: dict[str, object]) -> str | None:
        definition = rule.fee_item_definition
        if definition is None or not definition.billing_basis_template:
            return None

        return re.sub(
            r"\{([A-Za-z_][A-Za-z0-9_]*)\}",
            lambda match: self._format_template_value(context.get(match.group(1))),
            definition.billing_basis_template,
        )

    @staticmethod
    def _format_template_value(value: object) -> str:
        if isinstance(value, Decimal):
            return str(int(value)) if value == value.to_integral_value() else str(value)
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _split_country_regions(country_region: str) -> list[str]:
        regions = [
            item.strip()
            for item in re.split(r"[,，、/]+", country_region)
            if item.strip()
        ]
        return regions or [country_region]

    def _current_base_data_version_refs(self) -> str:
        sources = list(
            self.db.scalars(
                select(WipoDataSource)
                .where(WipoDataSource.is_active.is_(True))
                .order_by(WipoDataSource.source_code)
            )
        )
        refs = [
            {
                "source_code": source.source_code,
                "source_name": source.source_name,
                "source_url": source.source_url or source.official_url,
                "current_version": source.current_version,
                "current_version_id": source.current_version_id,
                "source_status_date": source.source_status_date.isoformat() if source.source_status_date else None,
                "last_published_at": source.last_published_at.isoformat() if source.last_published_at else None,
            }
            for source in sources
        ]
        return json.dumps(refs, ensure_ascii=False)

    def _base_data_snapshot_for_quote(self, country_region: str) -> str:
        rows = []
        for country in self._split_country_regions(country_region):
            entity = self._find_base_entity_for_country(country)
            if entity is None:
                rows.append(
                    {
                        "input_country_region": country,
                        "matched": False,
                        "note": "保存报价时未匹配到已发布国家基础数据；历史记录保留该缺口。",
                    }
                )
                continue
            rows.append(
                {
                    "input_country_region": country,
                    "matched": True,
                    "code": entity.code,
                    "name_zh": entity.name_zh,
                    "name_en": entity.name_en,
                    "data_type": entity.data_type,
                    "is_pct_member": entity.is_pct_member,
                    "is_paris_member": entity.is_paris_member,
                    "pct_entry_deadline_chapter_1": entity.pct_entry_deadline_chapter_1,
                    "source_version_id": entity.source_version_id,
                    "note": entity.note,
                    "snapshot_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        return json.dumps(rows, ensure_ascii=False)

    def _find_base_entity_for_country(self, country_region: str) -> WipoBaseEntity | None:
        candidates = base_entity_code_candidates(country_region)
        if candidates:
            entity = self.db.scalar(
                select(WipoBaseEntity)
                .where(WipoBaseEntity.code.in_(candidates), WipoBaseEntity.is_active.is_(True))
                .order_by(WipoBaseEntity.code)
            )
            if entity is not None:
                return entity
        return self.db.scalar(
            select(WipoBaseEntity)
            .where(
                WipoBaseEntity.name_zh == country_region,
                WipoBaseEntity.is_active.is_(True),
            )
        )

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


def base_entity_code_candidates(country_region: str) -> list[str]:
    normalized = country_region.strip().upper()
    aliases = {
        "美国": ["US"],
        "US": ["US"],
        "USA": ["US"],
        "EPO": ["EP"],
        "欧洲": ["EP"],
        "欧洲专利局": ["EP"],
        "EP": ["EP"],
        "EUIPO": ["EM"],
        "欧盟外观": ["EM"],
        "欧盟知识产权局": ["EM"],
        "EM": ["EM"],
        "日本": ["JP"],
        "JP": ["JP"],
        "韩国": ["KR"],
        "KR": ["KR"],
    }
    return aliases.get(country_region.strip(), aliases.get(normalized, [normalized] if re.fullmatch(r"[A-Z]{2}", normalized) else []))
