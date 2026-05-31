from __future__ import annotations

import argparse
from pathlib import Path
import sys

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.core.security import get_password_hash  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.user import Role, User  # noqa: E402


def create_admin(name: str, email: str, password: str) -> None:
    with SessionLocal() as db:
        admin_role = db.scalar(select(Role).where(Role.code == "admin"))
        if admin_role is None:
            admin_role = Role(code="admin", name="管理员")
            db.add(admin_role)
            db.flush()

        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                role_id=admin_role.id,
                name=name,
                email=email,
                password_hash=get_password_hash(password),
                status="active",
            )
            db.add(user)
        else:
            user.role_id = admin_role.id
            user.name = name
            user.password_hash = get_password_hash(password)
            user.status = "active"

        db.commit()
        print(f"Admin user ready: {email}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or reset an admin user.")
    parser.add_argument("--name", default="Admin")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    create_admin(name=args.name, email=args.email, password=args.password)


if __name__ == "__main__":
    main()
