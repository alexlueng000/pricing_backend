from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.pricing_rule import PricingRule, PricingRuleComponent
from app.repositories.base import BaseRepository


class PricingRuleRepository(BaseRepository[PricingRule]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, PricingRule)

    def find_active_rules(
        self,
        *,
        country_region: str,
        patent_type: str,
        filing_route: str,
        entity_type: str | None,
        quote_date: date,
    ) -> list[PricingRule]:
        stmt = (
            select(PricingRule)
            .options(
                selectinload(PricingRule.fee_item_definition),
                selectinload(PricingRule.components).selectinload(PricingRuleComponent.component_definition),
            )
            .where(
                PricingRule.country_region == country_region,
                PricingRule.patent_type == patent_type,
                PricingRule.filing_route == filing_route,
                PricingRule.status == "active",
                PricingRule.effective_date <= quote_date,
                or_(PricingRule.entity_type == entity_type, PricingRule.entity_type.is_(None)),
            )
            .order_by(PricingRule.fee_stage, PricingRule.id)
        )
        rules = list(self.db.scalars(stmt))
        return sorted(
            rules,
            key=lambda rule: (
                rule.fee_stage,
                rule.fee_item_definition.display_order if rule.fee_item_definition else 999999,
                rule.id,
            ),
        )

    def list_active(
        self,
        *,
        country_region: str | None = None,
        patent_type: str | None = None,
        filing_route: str | None = None,
        currency: str | None = None,
        status: str = "active",
    ) -> list[PricingRule]:
        stmt = (
            select(PricingRule)
            .options(
                selectinload(PricingRule.fee_item_definition),
                selectinload(PricingRule.components).selectinload(PricingRuleComponent.component_definition),
            )
            .where(PricingRule.status == status)
        )
        if country_region:
            stmt = stmt.where(PricingRule.country_region == country_region)
        if patent_type:
            stmt = stmt.where(PricingRule.patent_type == patent_type)
        if filing_route:
            stmt = stmt.where(PricingRule.filing_route.like(f"%{filing_route}%"))
        if currency:
            stmt = stmt.where(PricingRule.currency == currency)
        stmt = stmt.order_by(
            PricingRule.country_region,
            PricingRule.patent_type,
            PricingRule.filing_route,
            PricingRule.fee_stage,
        )
        return list(
            self.db.scalars(stmt)
        )

class PricingRuleComponentRepository(BaseRepository[PricingRuleComponent]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, PricingRuleComponent)

    def list_components(
        self,
        *,
        rule_id: int | None = None,
        component_code: str | None = None,
        status: str | None = None,
    ) -> list[PricingRuleComponent]:
        stmt = select(PricingRuleComponent).options(
            selectinload(PricingRuleComponent.pricing_rule),
            selectinload(PricingRuleComponent.component_definition),
        )
        if rule_id is not None:
            stmt = stmt.where(PricingRuleComponent.rule_id == rule_id)
        if component_code:
            stmt = stmt.where(PricingRuleComponent.component_code == component_code)
        if status:
            stmt = stmt.where(PricingRuleComponent.status == status)
        stmt = stmt.order_by(
            PricingRuleComponent.rule_id,
            PricingRuleComponent.component_code,
            PricingRuleComponent.effective_date.desc(),
            PricingRuleComponent.id.desc(),
        )
        return list(self.db.scalars(stmt))

    def has_overlapping_active_period(self, component: PricingRuleComponent) -> bool:
        if component.status not in {"enabled", "active"}:
            return False
        stmt = select(PricingRuleComponent).where(
            PricingRuleComponent.rule_id == component.rule_id,
            PricingRuleComponent.component_code == component.component_code,
            PricingRuleComponent.status.in_(("enabled", "active")),
            PricingRuleComponent.id != (component.id or 0),
            PricingRuleComponent.effective_date <= (component.expiry_date or date.max),
            or_(
                PricingRuleComponent.expiry_date.is_(None),
                PricingRuleComponent.expiry_date >= component.effective_date,
            ),
        )
        return self.db.scalar(stmt) is not None

    def has_same_effective_date(self, component: PricingRuleComponent) -> bool:
        stmt = select(PricingRuleComponent).where(
            PricingRuleComponent.rule_id == component.rule_id,
            PricingRuleComponent.component_code == component.component_code,
            PricingRuleComponent.effective_date == component.effective_date,
            PricingRuleComponent.id != (component.id or 0),
        )
        return self.db.scalar(stmt) is not None
