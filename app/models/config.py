from sqlalchemy import BigInteger, Boolean, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class ConfigDictionary(TimestampMixin, Base):
    __tablename__ = "config_dictionaries"
    __table_args__ = (
        UniqueConstraint("dict_type", "code", name="uk_config_dictionaries_type_code"),
        Index("idx_config_dictionaries_lookup", "dict_type", "is_enabled", "display_order"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    dict_type: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)


class CountryConfig(TimestampMixin, Base):
    __tablename__ = "country_configs"
    __table_args__ = (
        UniqueConstraint("country_code", name="uk_country_configs_code"),
        Index("idx_country_configs_enabled", "is_enabled", "display_order"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    country_code: Mapped[str] = mapped_column(String(50), nullable=False)
    country_name: Mapped[str] = mapped_column(String(100), nullable=False)
    country_aliases: Mapped[str | None] = mapped_column(Text, nullable=True)
    supported_patent_types: Mapped[str | None] = mapped_column(Text, nullable=True)
    supported_filing_routes: Mapped[str | None] = mapped_column(Text, nullable=True)
    supported_pct_entry_options: Mapped[str | None] = mapped_column(Text, nullable=True)
    supported_entity_types: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_currency: Mapped[str] = mapped_column(String(20), nullable=False)
    pct_deadline_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
