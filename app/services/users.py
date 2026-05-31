from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User
from app.repositories.users import RoleRepository, UserRepository
from app.schemas.user import UserAdminCreate


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.roles = RoleRepository(db)
        self.users = UserRepository(db)

    def get_by_email(self, email: str) -> User | None:
        return self.users.get_by_email(email)

    def list_active_users(self) -> list[User]:
        return self.users.list_active()

    def list_users(self) -> list[User]:
        return self.users.list_all()

    def create_user(self, payload: UserAdminCreate) -> User:
        existing = self.users.get_by_email(payload.email)
        if existing is not None:
            raise ValueError("Email already exists")

        role = self.roles.get_by_code(payload.role_code)
        if role is None:
            raise ValueError("Role not found")

        user = User(
            role_id=role.id,
            name=payload.name,
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            status=payload.status,
        )
        self.users.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self.users.get(user.id) or user
