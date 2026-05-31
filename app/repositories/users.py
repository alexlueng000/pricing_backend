from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.user import Role, User
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Role)

    def get_by_code(self, code: str) -> Role | None:
        return self.db.scalar(select(Role).where(Role.code == code))


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, User)

    def get(self, item_id: int) -> User | None:
        return self.db.scalar(
            select(User)
            .options(selectinload(User.role))
            .where(User.id == item_id)
        )

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(
            select(User)
            .options(selectinload(User.role))
            .where(User.email == email)
        )

    def list_active(self) -> list[User]:
        return list(
            self.db.scalars(
                select(User)
                .options(selectinload(User.role))
                .where(User.status == "active")
                .order_by(User.id.desc())
            )
        )

    def list_all(self) -> list[User]:
        return list(
            self.db.scalars(
                select(User)
                .options(selectinload(User.role))
                .order_by(User.id.desc())
            )
        )
