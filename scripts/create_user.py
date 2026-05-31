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


def create_user(name: str, email: str, password: str, role_code: str) -> None:
    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.code == role_code))
        if role is None:
            raise SystemExit(f"Role not found: {role_code}")

        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                role_id=role.id,
                name=name,
                email=email,
                password_hash=get_password_hash(password),
                status="active",
            )
            db.add(user)
        else:
            user.role_id = role.id
            user.name = name
            user.password_hash = get_password_hash(password)
            user.status = "active"

        db.commit()
        print(f"User ready: {email} ({role_code})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or reset a user account.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role-code", default="consultant", choices=["consultant", "admin"])
    args = parser.parse_args()
    create_user(
        name=args.name,
        email=args.email,
        password=args.password,
        role_code=args.role_code,
    )


if __name__ == "__main__":
    main()
