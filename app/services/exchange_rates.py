from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate
from app.repositories.exchange_rates import ExchangeRateRepository
from app.schemas.exchange_rate import ExchangeRateCreate


class ExchangeRateService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.rates = ExchangeRateRepository(db)

    def create_rate(self, payload: ExchangeRateCreate) -> ExchangeRate:
        existing = self.rates.get_by_date_currency(
            rate_date=payload.rate_date,
            currency=payload.currency,
        )
        if existing is not None:
            raise ValueError("该日期和币种的汇率已存在，请修改原记录或更换日期/币种")

        rate = ExchangeRate(**payload.model_dump())
        try:
            self.rates.add(rate)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("该日期和币种的汇率已存在，请修改原记录或更换日期/币种") from exc
        self.db.refresh(rate)
        return rate

    def get_quote_rate(self, *, currency: str, quote_date: date) -> ExchangeRate | None:
        return self.rates.get_for_currency_on_or_before(
            currency=currency,
            rate_date=quote_date,
        )

    def list_latest(
        self,
        *,
        currency: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ExchangeRate]:
        return self.rates.list_latest(
            currency=currency,
            date_from=date_from,
            date_to=date_to,
        )
