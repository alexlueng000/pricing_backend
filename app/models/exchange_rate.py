from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("rate_date", "currency", name="uk_exchange_rates_date_currency"),
        Index("idx_exchange_rates_currency_date", "currency", "rate_date"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    bank_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    buffer_type: Mapped[str] = mapped_column(String(30), default="absolute", nullable=False)
    buffer_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0, nullable=False)
    final_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    source: Mapped[str] = mapped_column(String(100), default="BOC", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
