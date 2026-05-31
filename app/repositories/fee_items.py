from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fee_item import FeeItemDefinition
from app.repositories.base import BaseRepository


class FeeItemDefinitionRepository(BaseRepository[FeeItemDefinition]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, FeeItemDefinition)

    def get_by_code(self, fee_item_code: str) -> FeeItemDefinition | None:
        return self.db.scalar(
            select(FeeItemDefinition).where(FeeItemDefinition.fee_item_code == fee_item_code)
        )

    def list_items(
        self,
        *,
        business_type: str | None = None,
        fee_stage: str | None = None,
        query: str | None = None,
        is_enabled: bool | None = None,
    ) -> list[FeeItemDefinition]:
        stmt = select(FeeItemDefinition)
        if business_type:
            stmt = stmt.where(FeeItemDefinition.business_type == business_type)
        if fee_stage:
            stmt = stmt.where(FeeItemDefinition.fee_stage == fee_stage)
        if query:
            stmt = stmt.where(FeeItemDefinition.fee_item_name.like(f"%{query}%"))
        if is_enabled is not None:
            stmt = stmt.where(FeeItemDefinition.is_enabled == is_enabled)
        stmt = stmt.order_by(
            FeeItemDefinition.business_type,
            FeeItemDefinition.fee_stage,
            FeeItemDefinition.display_order,
            FeeItemDefinition.id,
        )
        return list(self.db.scalars(stmt))
