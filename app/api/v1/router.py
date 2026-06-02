from fastapi import APIRouter

from app.api.v1.routes import (
    admin,
    auth,
    config,
    design_pricing,
    exchange_rates,
    fee_items,
    price_details,
    pricing_rules,
    quotes,
    wipo,
)

router = APIRouter()


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"message": "pong"}


router.include_router(auth.router)
router.include_router(config.router)
router.include_router(quotes.router)
router.include_router(admin.router)
router.include_router(design_pricing.router)
router.include_router(fee_items.router)
router.include_router(price_details.router)
router.include_router(pricing_rules.router)
router.include_router(exchange_rates.router)
router.include_router(wipo.router)

api_router = router
