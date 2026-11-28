"""Фабрика застосунку. Запуск: python -m uvicorn app.main:create_app --factory --host 127.0.0.1"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from app.database import create_db_engine, init_db, resolve_db_path
from app.routes import install_error_handlers, router


def create_app(db_path: str | Path | None = None, secret_key: str | None = None) -> FastAPI:
    """Створює застосунок із явно вказаною базою.

    Тести завжди передають шлях до тимчасової бази; без аргументу використовується
    PAPERTRAIL_DB або data/app.db.
    """
    engine = create_db_engine(resolve_db_path(db_path))
    init_db(engine)

    app = FastAPI(title="PaperTrail API", version="0.2")
    app.state.engine = engine
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    # Без PAPERTRAIL_SECRET_KEY токени чинні лише до перезапуску процесу.
    app.state.secret_key = (
        secret_key or os.environ.get("PAPERTRAIL_SECRET_KEY") or secrets.token_hex(32)
    )

    install_error_handlers(app)
    app.include_router(router)

    @app.get("/health", tags=["technical"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
