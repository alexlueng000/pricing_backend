from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.quote import Quote, QuoteFeeItem, QuoteInput
from app.repositories.base import BaseRepository


class QuoteRepository(BaseRepository[Quote]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Quote)

    def get_detail(self, quote_id: int) -> Quote | None:
        return self.db.scalar(
            select(Quote)
            .options(
                selectinload(Quote.inputs),
                selectinload(Quote.fee_items),
            )
            .where(Quote.id == quote_id)
        )

    def list_for_consultant(self, consultant_id: int) -> list[Quote]:
        return list(
            self.db.scalars(
                select(Quote)
                .where(Quote.consultant_id == consultant_id)
                .order_by(Quote.quote_date.desc(), Quote.id.desc())
            )
        )

    def list_all(self) -> list[Quote]:
        return list(
            self.db.scalars(
                select(Quote).order_by(Quote.quote_date.desc(), Quote.id.desc())
            )
        )


class QuoteInputRepository(BaseRepository[QuoteInput]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, QuoteInput)


class QuoteFeeItemRepository(BaseRepository[QuoteFeeItem]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, QuoteFeeItem)

    def replace_for_quote(self, quote_id: int, items: list[QuoteFeeItem]) -> list[QuoteFeeItem]:
        existing = list(
            self.db.scalars(select(QuoteFeeItem).where(QuoteFeeItem.quote_id == quote_id))
        )
        for item in existing:
            self.db.delete(item)
        for item in items:
            self.db.add(item)
        self.db.flush()
        return items

    def list_for_quote(self, quote_id: int) -> list[QuoteFeeItem]:
        return list(
            self.db.scalars(
                select(QuoteFeeItem)
                .where(QuoteFeeItem.quote_id == quote_id)
                .order_by(QuoteFeeItem.id)
            )
        )
