from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.fee_item import FeeComponentDefinition, FeeItemDefinition
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


class FeeComponentDefinitionRepository(BaseRepository[FeeComponentDefinition]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, FeeComponentDefinition)

    def get_by_code(self, component_code: str) -> FeeComponentDefinition | None:
        return self.db.scalar(
            select(FeeComponentDefinition).where(
                FeeComponentDefinition.component_code == component_code,
            )
        )

    def list_components(
        self,
        *,
        component_type: str | None = None,
        query: str | None = None,
        is_enabled: bool | None = None,
    ) -> list[FeeComponentDefinition]:
        stmt = select(FeeComponentDefinition)
        if component_type:
            stmt = stmt.where(FeeComponentDefinition.component_type == component_type)
        if query:
            stmt = stmt.where(
                or_(
                    FeeComponentDefinition.component_code.like(f"%{query}%"),
                    FeeComponentDefinition.component_name.like(f"%{query}%"),
                )
            )
        if is_enabled is not None:
            stmt = stmt.where(FeeComponentDefinition.is_enabled == is_enabled)
        stmt = stmt.order_by(
            FeeComponentDefinition.component_type,
            FeeComponentDefinition.display_order,
            FeeComponentDefinition.id,
        )
        return list(self.db.scalars(stmt))
