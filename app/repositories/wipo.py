from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.wipo import (
    WipoCountryTreatyStatus,
    WipoDataSource,
    WipoDataSourceHistory,
    WipoDetectionResult,
    WipoBaseEntity,
    WipoPctTimeLimit,
    WipoSourceVersion,
)
from app.repositories.base import BaseRepository


class WipoDataSourceRepository(BaseRepository[WipoDataSource]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, WipoDataSource)

    def list_items(self) -> list[WipoDataSource]:
        stmt = select(WipoDataSource).order_by(WipoDataSource.id)
        return list(self.db.scalars(stmt).all())

    def get_by_code(self, source_code: str) -> WipoDataSource | None:
        stmt = select(WipoDataSource).where(WipoDataSource.source_code == source_code)
        return self.db.scalar(stmt)


class WipoDataSourceHistoryRepository(BaseRepository[WipoDataSourceHistory]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, WipoDataSourceHistory)

    def list_for_source(self, source_id: int) -> list[WipoDataSourceHistory]:
        stmt = (
            select(WipoDataSourceHistory)
            .where(WipoDataSourceHistory.source_id == source_id)
            .order_by(WipoDataSourceHistory.created_at.desc(), WipoDataSourceHistory.id.desc())
        )
        return list(self.db.scalars(stmt).all())


class WipoDetectionResultRepository(BaseRepository[WipoDetectionResult]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, WipoDetectionResult)

    def list_for_source(self, source_id: int) -> list[WipoDetectionResult]:
        stmt = (
            select(WipoDetectionResult)
            .where(WipoDetectionResult.source_id == source_id)
            .order_by(WipoDetectionResult.detected_at.desc(), WipoDetectionResult.id.desc())
        )
        return list(self.db.scalars(stmt).all())


class WipoSourceVersionRepository(BaseRepository[WipoSourceVersion]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, WipoSourceVersion)

    def list_for_source(self, source_id: int) -> list[WipoSourceVersion]:
        stmt = (
            select(WipoSourceVersion)
            .where(WipoSourceVersion.source_id == source_id)
            .order_by(WipoSourceVersion.published_at.desc(), WipoSourceVersion.id.desc())
        )
        return list(self.db.scalars(stmt).all())


class WipoBaseEntityRepository(BaseRepository[WipoBaseEntity]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, WipoBaseEntity)

    def get_by_code(self, code: str) -> WipoBaseEntity | None:
        stmt = select(WipoBaseEntity).where(WipoBaseEntity.code == code)
        return self.db.scalar(stmt)

    def list_items(self) -> list[WipoBaseEntity]:
        stmt = select(WipoBaseEntity).order_by(WipoBaseEntity.data_type, WipoBaseEntity.code)
        return list(self.db.scalars(stmt).all())


class WipoCountryTreatyStatusRepository(BaseRepository[WipoCountryTreatyStatus]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, WipoCountryTreatyStatus)

    def list_items(self) -> list[WipoCountryTreatyStatus]:
        stmt = select(WipoCountryTreatyStatus).order_by(WipoCountryTreatyStatus.country_code)
        return list(self.db.scalars(stmt).all())


class WipoPctTimeLimitRepository(BaseRepository[WipoPctTimeLimit]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, WipoPctTimeLimit)

    def list_items(self) -> list[WipoPctTimeLimit]:
        stmt = select(WipoPctTimeLimit).order_by(WipoPctTimeLimit.country_code)
        return list(self.db.scalars(stmt).all())
