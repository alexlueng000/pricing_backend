from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.design_pricing import DesignPricingConfig
from app.repositories.base import BaseRepository


class DesignPricingConfigRepository(BaseRepository[DesignPricingConfig]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, DesignPricingConfig)

    def list_active(
        self,
        *,
        business_type: str = "design",
        status: str = "active",
    ) -> list[DesignPricingConfig]:
        stmt = (
            select(DesignPricingConfig)
            .options(selectinload(DesignPricingConfig.tiers))
            .where(
                DesignPricingConfig.business_type == business_type,
                DesignPricingConfig.status == status,
            )
            .order_by(DesignPricingConfig.country_region, DesignPricingConfig.id)
        )
        return list(self.db.scalars(stmt))
