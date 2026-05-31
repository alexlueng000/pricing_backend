from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ExchangeRateBase(BaseModel):
    rate_date: date
    currency: str
    bank_rate: Decimal
    buffer_type: str = "absolute"
    buffer_value: Decimal = Decimal("0.000000")
    final_rate: Decimal
    source: str = "BOC"


class ExchangeRateCreate(ExchangeRateBase):
    pass


class ExchangeRateRead(ExchangeRateBase, ORMModel):
    id: int
    created_at: datetime

