from datetime import date

from sqlalchemy.orm import Session

from app.models.price_detail import PriceDetail
from app.repositories.price_details import PriceDetailRepository
from app.schemas.price_detail import PriceDetailCreate

LEGACY_FEE_TYPES = {"official_fee", "foreign_agent_fee", "local_agent_fee"}
STRUCTURED_FEE_TYPES = {
    "target_official_fee",
    "our_service_fee",
    "associate_service_fee",
    "third_party_disbursement",
}
FEE_TYPES = LEGACY_FEE_TYPES | STRUCTURED_FEE_TYPES
DISPLAY_SECTIONS = {"main_table", "disbursement_section"}


class PriceDetailService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.details = PriceDetailRepository(db)

    def create_detail(self, payload: PriceDetailCreate) -> PriceDetail:
        data = self._normalize(payload.model_dump())
        detail = PriceDetail(**data)
        self.details.add(detail)
        self.db.commit()
        self.db.refresh(detail)
        return detail

    def update_detail(self, detail_id: int, payload: PriceDetailCreate) -> PriceDetail | None:
        detail = self.details.get(detail_id)
        if detail is None:
            return None
        data = self._normalize(payload.model_dump())
        for key, value in data.items():
            setattr(detail, key, value)
        self.db.commit()
        self.db.refresh(detail)
        return detail

    def list_details(
        self,
        *,
        country_region: str | None = None,
        patent_type: str | None = None,
        filing_route: str | None = None,
        fee_type: str | None = None,
        status: str | None = None,
    ) -> list[PriceDetail]:
        return self.details.list_details(
            country_region=country_region,
            patent_type=patent_type,
            filing_route=filing_route,
            fee_type=fee_type,
            status=status,
        )

    @staticmethod
    def _normalize(data: dict[str, object]) -> dict[str, object]:
        fee_type = str(data.get("fee_type") or "").strip()
        if fee_type not in FEE_TYPES:
            raise ValueError("费用类型不合法")
        if not str(data.get("display_category") or "").strip():
            raise ValueError("展示分类不能为空")
        if not str(data.get("amount_formula") or "").strip():
            raise ValueError("金额不能为空")
        display_section = str(data.get("display_section") or "").strip()
        if display_section and display_section not in DISPLAY_SECTIONS:
            raise ValueError("展示分区只能为 main_table / disbursement_section")
        if data.get("expiry_date") and data["expiry_date"] < data["effective_date"]:
            raise ValueError("失效日期不得早于生效日期")

        for key, value in list(data.items()):
            if isinstance(value, str):
                data[key] = value.strip() or None
        data["fee_type"] = fee_type
        if not data.get("display_section"):
            data["display_section"] = default_display_section(fee_type)
        data["status"] = data.get("status") or "active"
        return data


def default_display_section(fee_type: str) -> str:
    if fee_type == "third_party_disbursement":
        return "disbursement_section"
    return "main_table"
