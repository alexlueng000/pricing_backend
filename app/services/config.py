from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.config import ConfigDictionary, CountryConfig
from app.models.wipo import WipoBaseEntity
from app.repositories.config import ConfigDictionaryRepository, CountryConfigRepository
from app.schemas.config import ConfigDictionaryCreate, CountryConfigCreate

COUNTRY_CODE_BY_NAME = {
    "美国": "US",
    "EPO": "EPO",
    "EUIPO": "EUIPO",
    "日本": "JP",
    "韩国": "KR",
}


class ConfigService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.dictionaries = ConfigDictionaryRepository(db)
        self.countries = CountryConfigRepository(db)

    def list_dictionaries(
        self,
        *,
        dict_type: str | None = None,
        is_enabled: bool | None = None,
    ) -> list[ConfigDictionary]:
        return self.dictionaries.list_items(dict_type=dict_type, is_enabled=is_enabled)

    def create_dictionary(self, payload: ConfigDictionaryCreate) -> ConfigDictionary:
        item = ConfigDictionary(**self._normalize(payload.model_dump()))
        self.dictionaries.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_dictionary(self, item_id: int, payload: ConfigDictionaryCreate) -> ConfigDictionary | None:
        item = self.dictionaries.get(item_id)
        if item is None:
            return None
        for key, value in self._normalize(payload.model_dump()).items():
            setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_countries(self, *, is_enabled: bool | None = None) -> list[CountryConfig]:
        return self.countries.list_items(is_enabled=is_enabled)

    def create_country(self, payload: CountryConfigCreate) -> CountryConfig:
        item = CountryConfig(**self._normalize_country(payload.model_dump()))
        existing = self.db.scalar(
            select(CountryConfig).where(
                (CountryConfig.country_code == item.country_code)
                | (CountryConfig.country_name == item.country_name)
            )
        )
        if existing is not None:
            raise ValueError("该国家/地区配置已存在，请编辑已有配置")
        self.countries.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_country(self, item_id: int, payload: CountryConfigCreate) -> CountryConfig | None:
        item = self.countries.get(item_id)
        if item is None:
            return None
        for key, value in self._normalize_country(payload.model_dump()).items():
            setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    @staticmethod
    def _normalize(data: dict[str, object]) -> dict[str, object]:
        for key, value in list(data.items()):
            if isinstance(value, str):
                data[key] = value.strip() or None
        return data

    @classmethod
    def _normalize_country(cls, data: dict[str, object]) -> dict[str, object]:
        normalized = cls._normalize(data)
        country_name = normalized.get("country_name")
        if not isinstance(country_name, str):
            raise ValueError("国家/地区必填")
        country_code = COUNTRY_CODE_BY_NAME.get(country_name)
        if country_code is None:
            payload_code = normalized.get("country_code")
            country_code = str(payload_code).strip().upper() if isinstance(payload_code, str) and payload_code.strip() else None
        if country_code is not None:
            entity = self.db.scalar(
                select(WipoBaseEntity).where(
                    (WipoBaseEntity.code == country_code)
                    | (WipoBaseEntity.name_zh == country_name)
                )
            )
            if entity is not None:
                country_code = entity.code
        if country_code is None:
            raise ValueError("国家/地区不在可维护范围内")
        normalized["country_code"] = country_code
        normalized["default_entity_type"] = None
        if not normalized.get("entity_type_enabled"):
            normalized["supported_entity_types"] = None
        return normalized
