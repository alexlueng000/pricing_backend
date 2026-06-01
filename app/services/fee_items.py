import re

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.fee_item import FeeComponentDefinition, FeeItemDefinition
from app.repositories.fee_items import FeeComponentDefinitionRepository, FeeItemDefinitionRepository
from app.schemas.fee_item import FeeComponentDefinitionCreate, FeeItemDefinitionCreate

COMPONENT_TYPES = {"official_fee", "foreign_agent_fee", "local_agent_fee"}
FEE_ITEM_CODE_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")


class FeeItemDefinitionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.items = FeeItemDefinitionRepository(db)
        self.components = FeeComponentDefinitionRepository(db)

    def create_item(self, payload: FeeItemDefinitionCreate) -> FeeItemDefinition:
        self._validate_item_payload(payload)
        data = self._normalized_item_data(payload)
        if self.items.get_by_code(str(data["fee_item_code"])):
            raise ValueError("费用项编码已存在")
        item = FeeItemDefinition(**data)
        try:
            self.items.add(item)
            self.db.commit()
            self.db.refresh(item)
            return item
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("费用项编码已存在") from exc
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise ValueError("数据库写入失败") from exc

    def update_item(self, item_id: int, payload: FeeItemDefinitionCreate) -> FeeItemDefinition | None:
        item = self.items.get(item_id)
        if item is None:
            return None
        self._validate_item_payload(payload)
        data = self._normalized_item_data(payload)
        existing = self.items.get_by_code(str(data["fee_item_code"]))
        if existing is not None and existing.id != item_id:
            raise ValueError("费用项编码已存在")
        for key, value in data.items():
            setattr(item, key, value)
        try:
            self.db.commit()
            self.db.refresh(item)
            return item
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("费用项编码已存在") from exc
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise ValueError("数据库写入失败") from exc

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

    def create_component(self, payload: FeeComponentDefinitionCreate) -> FeeComponentDefinition:
        self._validate_component_payload(payload)
        if self.components.get_by_code(payload.component_code):
            raise ValueError("小项编码不能重复")
        component = FeeComponentDefinition(**payload.model_dump())
        self.components.add(component)
        self.db.commit()
        self.db.refresh(component)
        return component

    def update_component(
        self,
        component_id: int,
        payload: FeeComponentDefinitionCreate,
    ) -> FeeComponentDefinition | None:
        component = self.components.get(component_id)
        if component is None:
            return None
        self._validate_component_payload(payload)
        existing = self.components.get_by_code(payload.component_code)
        if existing is not None and existing.id != component_id:
            raise ValueError("小项编码不能重复")
        for key, value in payload.model_dump().items():
            setattr(component, key, value)
        self.db.commit()
        self.db.refresh(component)
        return component

    def set_component_enabled(
        self,
        component_id: int,
        is_enabled: bool,
    ) -> FeeComponentDefinition | None:
        component = self.components.get(component_id)
        if component is None:
            return None
        component.is_enabled = is_enabled
        self.db.commit()
        self.db.refresh(component)
        return component

    def list_components(
        self,
        *,
        component_type: str | None = None,
        query: str | None = None,
        is_enabled: bool | None = None,
    ) -> list[FeeComponentDefinition]:
        return self.components.list_components(
            component_type=component_type,
            query=query,
            is_enabled=is_enabled,
        )

    @staticmethod
    def _validate_item_payload(payload: FeeItemDefinitionCreate) -> None:
        required_fields = (
            ("fee_item_code", "费用项编码"),
            ("fee_item_name", "费用项名称"),
            ("business_type", "业务类型"),
            ("fee_stage", "费用阶段"),
            ("billing_basis_type", "计费依据类型"),
        )
        for field, label in required_fields:
            value = getattr(payload, field)
            if value is None or str(value).strip() == "":
                raise ValueError(f"{label}不能为空")
        if not FEE_ITEM_CODE_PATTERN.fullmatch(payload.fee_item_code.strip()):
            raise ValueError("费用项编码格式错误，请使用大写英文字母、数字和下划线，且不能以数字开头。")
        if type(payload.display_order) is not int:
            raise ValueError("显示顺序必须为数字")
        if payload.is_enabled is None:
            raise ValueError("状态不能为空")

    @staticmethod
    def _normalized_item_data(payload: FeeItemDefinitionCreate) -> dict[str, object]:
        data = payload.model_dump()
        for field in ("fee_item_code", "fee_item_name", "business_type", "fee_stage", "billing_basis_type"):
            data[field] = str(data[field]).strip()
        for field in ("billing_basis_template", "remark"):
            value = data.get(field)
            data[field] = str(value).strip() if value is not None and str(value).strip() else None
        return data

    @staticmethod
    def _validate_component_payload(payload: FeeComponentDefinitionCreate) -> None:
        required_fields = (
            ("component_code", "小项编码"),
            ("component_name", "小项名称"),
            ("component_type", "费用类型"),
            ("default_currency", "默认币种"),
        )
        for field, label in required_fields:
            value = getattr(payload, field)
            if value is None or str(value).strip() == "":
                raise ValueError(f"{label}不能为空")
        if payload.component_type not in COMPONENT_TYPES:
            raise ValueError("component_type 只能为 official_fee / foreign_agent_fee / local_agent_fee")
