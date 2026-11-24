"""Спільні фікстури. Кожен тест працює з власною файловою базою в tmp_path."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True)
def _forbid_working_database(tmp_path, monkeypatch):
    """Навіть без явного шляху застосунок не повинен потрапити в data/app.db."""
    monkeypatch.setenv("PAPERTRAIL_DB", str(tmp_path / "guard.db"))


@pytest.fixture
def db_file(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def app(db_file):
    return create_app(db_file, secret_key="test-secret")


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
