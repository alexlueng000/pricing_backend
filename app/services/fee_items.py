from sqlalchemy.orm import Session

from app.models.fee_item import FeeItemDefinition
from app.repositories.fee_items import FeeItemDefinitionRepository
from app.schemas.fee_item import FeeItemDefinitionCreate


class FeeItemDefinitionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.items = FeeItemDefinitionRepository(db)

    def create_item(self, payload: FeeItemDefinitionCreate) -> FeeItemDefinition:
        item = FeeItemDefinition(**payload.model_dump())
        self.items.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_item(self, item_id: int, payload: FeeItemDefinitionCreate) -> FeeItemDefinition | None:
        item = self.items.get(item_id)
        if item is None:
            return None
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def set_enabled(self, item_id: int, is_enabled: bool) -> FeeItemDefinition | None:
        item = self.items.get(item_id)
        if item is None:
            return None
        item.is_enabled = is_enabled
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_items(
        self,
        *,
        business_type: str | None = None,
        fee_stage: str | None = None,
        query: str | None = None,
        is_enabled: bool | None = None,
    ) -> list[FeeItemDefinition]:
        return self.items.list_items(
            business_type=business_type,
            fee_stage=fee_stage,
            query=query,
            is_enabled=is_enabled,
        )
