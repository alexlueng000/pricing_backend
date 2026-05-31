from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.pricing_rule import PricingRule
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
        return list(self.db.scalars(stmt))

    def list_active(
        self,
        *,
        country_region: str | None = None,
        patent_type: str | None = None,
        filing_route: str | None = None,
        currency: str | None = None,
        status: str = "active",
    ) -> list[PricingRule]:
        stmt = select(PricingRule).where(PricingRule.status == status)
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
