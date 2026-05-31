from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.design_pricing import DesignPricingConfig
from app.repositories.design_pricing import DesignPricingConfigRepository
from app.schemas.design_pricing import DesignPricingConfigCreate


class DesignPricingConfigService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.configs = DesignPricingConfigRepository(db)

    def create_config(self, payload: DesignPricingConfigCreate) -> DesignPricingConfig:
        config = DesignPricingConfig(**payload.model_dump())
        self.configs.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def list_active_configs(
        self,
        *,
        business_type: str = "design",
        status: str = "active",
    ) -> list[DesignPricingConfig]:
        return self.configs.list_active(business_type=business_type, status=status)

    def find_config(
        self,
        *,
        country_region: str,
        business_type: str = "design",
        examination_category: str | None = None,
    ) -> DesignPricingConfig | None:
        configs = self.list_active_configs(business_type=business_type)
        matching_configs = [
            config
            for config in configs
            if self._config_matches_country(config, country_region)
        ]
        if not matching_configs:
            return None

        if examination_category:
            for config in matching_configs:
                if config.examination_category == examination_category:
                    return config

        for config in matching_configs:
            if config.examination_category in {None, "", "default_substantive"}:
                return config
        return matching_configs[0]

    def calculate_total_price(
        self,
        *,
        config: DesignPricingConfig,
        design_count: int,
    ) -> Decimal:
        if design_count <= 1:
            return Decimal(config.base_price)
        if not config.allow_multiple_designs:
            return Decimal(config.base_price) * Decimal(design_count)
        if config.multiple_design_pricing_mode == "single_design_multiply":
            return Decimal(config.base_price) * Decimal(design_count)
        if config.multiple_design_pricing_mode == "multiple_price_table":
            tier_price = self._tier_price(config, design_count)
            if tier_price is not None:
                return tier_price
            return Decimal(config.base_price) * Decimal(design_count)
        return Decimal(config.base_price) * Decimal(design_count)

    @staticmethod
    def _tier_price(config: DesignPricingConfig, design_count: int) -> Decimal | None:
        for tier in sorted(config.tiers, key=lambda item: item.min_design_count):
            if design_count < tier.min_design_count:
                continue
            if tier.max_design_count is not None and design_count > tier.max_design_count:
                continue
            return Decimal(tier.total_price)
        return None

    @staticmethod
    def _config_matches_country(config: DesignPricingConfig, country_region: str) -> bool:
        tokens = [
            config.country_region,
            *(config.country_aliases or "").replace("，", ",").replace("、", ",").split(","),
        ]
        normalized_region = country_region.strip().casefold()
        return any(token.strip().casefold() == normalized_region for token in tokens if token.strip())
