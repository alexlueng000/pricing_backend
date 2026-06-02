from pydantic import BaseModel

from app.schemas.common import TimestampSchema


class ConfigDictionaryBase(BaseModel):
    dict_type: str
    code: str
    name: str
    display_order: int = 100
    is_enabled: bool = True
    remark: str | None = None


class ConfigDictionaryCreate(ConfigDictionaryBase):
    pass


class ConfigDictionaryRead(ConfigDictionaryBase, TimestampSchema):
    id: int


class CountryConfigBase(BaseModel):
    country_code: str
    country_name: str
    country_aliases: str | None = None
    supported_patent_types: str | None = None
    supported_filing_routes: str | None = None
    supported_entity_types: str | None = None
    entity_type_enabled: bool = True
    default_entity_type: str | None = None
    default_currency: str
    pct_deadline_months: int | None = None
    display_order: int = 100
    is_enabled: bool = True
    remark: str | None = None


class CountryConfigCreate(CountryConfigBase):
    pass


class CountryConfigRead(CountryConfigBase, TimestampSchema):
    id: int
