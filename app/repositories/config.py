from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.config import ConfigDictionary, CountryConfig
from app.repositories.base import BaseRepository


class ConfigDictionaryRepository(BaseRepository[ConfigDictionary]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ConfigDictionary)

    def list_items(self, *, dict_type: str | None = None, is_enabled: bool | None = None) -> list[ConfigDictionary]:
        stmt = select(ConfigDictionary)
        if dict_type:
            stmt = stmt.where(ConfigDictionary.dict_type == dict_type)
        if is_enabled is not None:
            stmt = stmt.where(ConfigDictionary.is_enabled == is_enabled)
        stmt = stmt.order_by(ConfigDictionary.dict_type, ConfigDictionary.display_order, ConfigDictionary.id)
        return list(self.db.scalars(stmt))


class CountryConfigRepository(BaseRepository[CountryConfig]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, CountryConfig)

    def list_items(self, *, is_enabled: bool | None = None) -> list[CountryConfig]:
        stmt = select(CountryConfig)
        if is_enabled is not None:
            stmt = stmt.where(CountryConfig.is_enabled == is_enabled)
        stmt = stmt.order_by(CountryConfig.display_order, CountryConfig.id)
        return list(self.db.scalars(stmt))
