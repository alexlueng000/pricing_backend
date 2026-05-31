from datetime import datetime

from app.schemas.common import ORMModel, TimestampSchema


class RoleRead(ORMModel):
    id: int
    code: str
    name: str
    created_at: datetime


class UserBase(ORMModel):
    name: str
    email: str
    status: str = "active"


class UserCreate(UserBase):
    role_id: int
    password: str


class UserAdminCreate(UserBase):
    role_code: str = "consultant"
    password: str


class UserRead(UserBase, TimestampSchema):
    id: int
    role_id: int
    role: RoleRead | None = None
