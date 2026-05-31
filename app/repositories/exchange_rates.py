from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate
from app.repositories.base import BaseRepository


class ExchangeRateRepository(BaseRepository[ExchangeRate]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ExchangeRate)

    def get_for_currency_on_or_before(
        self,
        *,
        currency: str,
        rate_date: date,
    ) -> ExchangeRate | None:
        return self.db.scalar(
            select(ExchangeRate)
            .where(
                func.upper(ExchangeRate.currency) == currency.upper(),
                ExchangeRate.rate_date <= rate_date,
            )
            .order_by(ExchangeRate.rate_date.desc())
            .limit(1)
        )

    def get_by_date_currency(
        self,
        *,
        rate_date: date,
        currency: str,
    ) -> ExchangeRate | None:
        return self.db.scalar(
            select(ExchangeRate).where(
                ExchangeRate.rate_date == rate_date,
                ExchangeRate.currency == currency,
            )
        )

    def list_latest(
        self,
        *,
        currency: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ExchangeRate]:
        stmt = select(ExchangeRate)
        if currency:
            stmt = stmt.where(ExchangeRate.currency == currency)
        if date_from:
            stmt = stmt.where(ExchangeRate.rate_date >= date_from)
        if date_to:
            stmt = stmt.where(ExchangeRate.rate_date <= date_to)
        stmt = stmt.order_by(
            ExchangeRate.currency,
            ExchangeRate.rate_date.desc(),
        )
        return list(
            self.db.scalars(stmt)
        )
