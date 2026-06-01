from sqlalchemy.orm import Session

from app.models.pricing_rule import PricingRuleComponent
from app.repositories.fee_items import FeeComponentDefinitionRepository
from app.repositories.pricing_rules import PricingRuleComponentRepository, PricingRuleRepository
from app.schemas.pricing_rule import PricingRuleComponentCreate

COMPONENT_TYPES = {"official_fee", "foreign_agent_fee", "local_agent_fee"}


class PricingRuleComponentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.rules = PricingRuleRepository(db)
        self.components = FeeComponentDefinitionRepository(db)
        self.rule_components = PricingRuleComponentRepository(db)

    def create_component(self, payload: PricingRuleComponentCreate) -> PricingRuleComponent:
        data = payload.model_dump()
        self._validate_payload(data)
        component = PricingRuleComponent(**data)
        if self.rule_components.has_same_effective_date(component):
            raise ValueError("同一规则、小项和生效日期不能重复")
        if self.rule_components.has_overlapping_active_period(component):
            raise ValueError("同一规则和费用小项的启用版本生效区间不得重叠")
        self.rule_components.add(component)
        self.db.commit()
        self.db.refresh(component)
        return component

    def update_component(
        self,
        component_id: int,
        payload: PricingRuleComponentCreate,
    ) -> PricingRuleComponent | None:
        component = self.rule_components.get(component_id)
        if component is None:
            return None
        data = payload.model_dump()
        self._validate_payload(data)
        for key, value in data.items():
            setattr(component, key, value)
        if self.rule_components.has_same_effective_date(component):
            raise ValueError("同一规则、小项和生效日期不能重复")
        if self.rule_components.has_overlapping_active_period(component):
            raise ValueError("同一规则和费用小项的启用版本生效区间不得重叠")
        self.db.commit()
        self.db.refresh(component)
        return component

    def list_components(
        self,
        *,
        rule_id: int | None = None,
        component_code: str | None = None,
        status: str | None = None,
    ) -> list[PricingRuleComponent]:
        return self.rule_components.list_components(
            rule_id=rule_id,
            component_code=component_code,
            status=status,
        )

    def _validate_payload(self, data: dict[str, object]) -> None:
        if data.get("component_type") not in COMPONENT_TYPES:
            raise ValueError("component_type 只能为 official_fee / foreign_agent_fee / local_agent_fee")
        if self.rules.get(int(data["rule_id"])) is None:
            raise ValueError("关联费用规则不存在")
        component = self.components.get_by_code(str(data["component_code"]))
        if component is None:
            raise ValueError("关联费用小项不存在")
        if component.component_type != data.get("component_type"):
            raise ValueError("component_type 必须与费用小项库一致")
        value = data.get("amount_formula")
        if value is None or str(value).strip() == "":
            raise ValueError("金额/公式不能为空")
        if not data.get("effective_date"):
            raise ValueError("生效日期不能为空")
        if data.get("expiry_date") and data["expiry_date"] < data["effective_date"]:
            raise ValueError("失效日期不得早于生效日期")
