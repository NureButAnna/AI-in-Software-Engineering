"""Бізнес-правила. Не залежить від FastAPI; транзакціями керує сервіс."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import security
from app.errors import DuplicateEmail, InvalidCredentials
from app.models import User, utcnow

# Хеш для вирівнювання часу відповіді, коли email невідомий.
_DUMMY_HASH = security.hash_password("not-a-real-password")


def register_user(db: Session, email: str, password: str) -> User:
    """US-01: новий користувач з унікальним email; автоматичного входу немає."""
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise DuplicateEmail()
    now = utcnow()
    user = User(
        email=email,
        password_hash=security.hash_password(password),
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateEmail() from None
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    """US-02: однакова помилка для невідомого email і хибного пароля."""
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        security.verify_password(password, _DUMMY_HASH)
        raise InvalidCredentials()
    if not security.verify_password(password, user.password_hash):
        raise InvalidCredentials()
    return user


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)
