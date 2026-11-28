"""Каркас: GET /health, ініціалізація бази, ізоляція від робочої бази (T20, T21)."""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import DEFAULT_DB_PATH, resolve_db_path
from app.main import create_app
from app.models import User


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_t21_tests_never_use_working_database(tmp_path):
    guard = tmp_path / "guard.db"
    assert resolve_db_path() == guard
    assert resolve_db_path(tmp_path / "explicit.db") == tmp_path / "explicit.db"
    assert guard != DEFAULT_DB_PATH


def test_init_creates_all_tables(db_file, app):
    with sqlite3.connect(db_file) as conn:
        tables = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
    assert {
        "users", "cases", "tasks", "documents", "institutions",
        "reminders", "case_documents", "case_institutions",
    } <= tables


def test_foreign_keys_enabled_for_every_connection(app):
    for _ in range(2):
        with app.state.engine.connect() as conn:
            assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_t20_data_survives_restart_and_init_is_idempotent(db_file):
    first = create_app(db_file, secret_key="s")
    with Session(first.state.engine) as db:
        db.add(User(email="a@example.com", password_hash="x"))
        db.commit()
    first.state.engine.dispose()

    second = create_app(db_file, secret_key="s")  # повторна ініціалізація тієї самої БД
    with TestClient(second) as client:
        assert client.get("/health").status_code == 200
    with Session(second.state.engine) as db:
        assert [u.email for u in db.query(User)] == ["a@example.com"]
