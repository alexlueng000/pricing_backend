from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.price_detail import PriceDetail
from app.repositories.base import BaseRepository


class PriceDetailRepository(BaseRepository[PriceDetail]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, PriceDetail)

    def list_details(
        self,
        *,
        country_region: str | None = None,
        patent_type: str | None = None,
        filing_route: str | None = None,
        fee_type: str | None = None,
        status: str | None = None,
    ) -> list[PriceDetail]:
        stmt = select(PriceDetail)
        if country_region:
            stmt = stmt.where(PriceDetail.country_region == country_region)
        if patent_type:
            stmt = stmt.where(PriceDetail.patent_type == patent_type)
        if filing_route:
            stmt = stmt.where(PriceDetail.filing_route == filing_route)
        if fee_type:
            stmt = stmt.where(PriceDetail.fee_type == fee_type)
        if status:
            stmt = stmt.where(PriceDetail.status == status)
        stmt = stmt.order_by(
            PriceDetail.country_region,
            PriceDetail.patent_type,
            PriceDetail.filing_route,
            PriceDetail.fee_stage,
            PriceDetail.display_order,
            PriceDetail.id,
        )
        return list(self.db.scalars(stmt))

    def find_active_details(
        self,
        *,
        country_region: str,
        patent_type: str,
        filing_route: str,
        entity_type: str | None,
        quote_date: date,
    ) -> list[PriceDetail]:
        stmt = (
            select(PriceDetail)
            .where(
                PriceDetail.country_region == country_region,
                PriceDetail.patent_type == patent_type,
                PriceDetail.filing_route == filing_route,
                PriceDetail.status == "active",
                PriceDetail.effective_date <= quote_date,
                or_(PriceDetail.expiry_date.is_(None), PriceDetail.expiry_date >= quote_date),
                or_(PriceDetail.entity_type == entity_type, PriceDetail.entity_type.is_(None)),
            )
            .order_by(
                PriceDetail.fee_stage,
                PriceDetail.display_order,
                PriceDetail.display_category,
                PriceDetail.id,
            )
        )
        return list(self.db.scalars(stmt))
