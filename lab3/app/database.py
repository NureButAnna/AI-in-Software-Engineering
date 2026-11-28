"""Підключення до SQLite: шлях до бази, двигун, сесії, ініціалізація таблиць."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import DeclarativeBase

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"


class Base(DeclarativeBase):
    """Базовий клас моделей (див. app/models.py)."""


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    """Явний шлях > змінна PAPERTRAIL_DB > data/app.db."""
    if db_path is not None:
        return Path(db_path)
    from_env = os.environ.get("PAPERTRAIL_DB")
    return Path(from_env) if from_env else DEFAULT_DB_PATH


def create_db_engine(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = URL.create("sqlite", database=str(db_path))
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):  # noqa: ANN001
        # SQLite не перевіряє зовнішні ключі, доки їх не ввімкнути для кожного з'єднання.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def init_db(engine: Engine) -> None:
    """Створює відсутні таблиці. Повторний виклик не змінює наявних даних."""
    from app import models  # noqa: F401  (реєструє таблиці в Base.metadata)

    Base.metadata.create_all(engine)
