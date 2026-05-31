from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.repositories.users import UserRepository


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def authenticate(self, *, email: str, password: str) -> User | None:
        user = self.users.get_by_email(email)
        if user is None or user.status != "active":
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def build_token(user: User) -> str:
        return create_access_token(subject=str(user.id))

