"""Наскрізне: єдина форма помилок і відсутність внутрішніх деталей (T22)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import services
from app.main import create_app


def assert_shape(response, status, code):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["details"], list)


def test_t22_all_error_kinds_share_one_shape(client, auth):
    assert_shape(client.get("/api/v1/cases"), 401, "AUTH_REQUIRED")
    assert_shape(client.get("/api/v1/cases/999", headers=auth), 404, "NOT_FOUND")
    assert_shape(client.post("/api/v1/cases", json={}, headers=auth), 422, "VALIDATION_ERROR")
    assert_shape(client.get("/api/v1/cases/abc", headers=auth), 422, "VALIDATION_ERROR")
    created = client.post("/api/v1/cases", json={"title": "A"}, headers=auth).json()
    assert_shape(
        client.patch(f"/api/v1/cases/{created['id']}/status", json={"status": "APPROVED"}, headers=auth),
        409, "INVALID_STATE_TRANSITION",
    )


def test_t22_unknown_url_uses_same_shape(client):
    assert_shape(client.get("/api/v1/nope"), 404, "NOT_FOUND")


def test_t22_wrong_method_uses_same_shape(client, auth):
    response = client.put("/api/v1/cases", json={}, headers=auth)
    assert response.status_code == 405
    assert set(response.json()["error"]) == {"code", "message", "details"}


def test_t22_validation_details_name_the_field(client, auth):
    response = client.post("/api/v1/cases", json={"title": " ", "deadline": "x"}, headers=auth)
    fields = {d["field"] for d in response.json()["error"]["details"]}
    assert fields == {"title", "deadline"}


def test_t22_unexpected_error_leaks_no_sql_paths_or_traceback(app, auth, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("SELECT * FROM users /home/secret/app.db Traceback")

    monkeypatch.setattr(services, "list_cases", boom)
    with TestClient(app, raise_server_exceptions=False) as client:
        client.post("/api/v1/auth/register", json={"email": "z@example.com", "password": "examplePass8"})
        token = client.post(
            "/api/v1/auth/login", json={"email": "z@example.com", "password": "examplePass8"}
        ).json()["access_token"]
        response = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token}"})
    assert_shape(response, 500, "INTERNAL_ERROR")
    for leaked in ("SELECT", "/home", "Traceback", "RuntimeError", "secret"):
        assert leaked not in response.text


def test_t22_openapi_documentation_is_available(client):
    schema = client.get("/openapi.json").json()
    paths = set(schema["paths"])
    assert {
        "/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/cases", "/api/v1/cases/{case_id}",
        "/api/v1/cases/{case_id}/status", "/api/v1/dashboard", "/health",
    } == paths
    assert client.get("/docs").status_code == 200


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/cases"), ("get", "/api/v1/cases"), ("get", "/api/v1/cases/1"),
        ("patch", "/api/v1/cases/1"), ("patch", "/api/v1/cases/1/status"),
        ("delete", "/api/v1/cases/1"), ("get", "/api/v1/dashboard"),
    ],
)
def test_t05_every_protected_route_requires_token(client, method, path):
    response = getattr(client, method)(path)
    assert_shape(response, 401, "AUTH_REQUIRED")


def test_create_app_without_path_uses_environment_database(tmp_path, monkeypatch):
    target = tmp_path / "from_env.db"
    monkeypatch.setenv("PAPERTRAIL_DB", str(target))
    app = create_app(secret_key="s")
    app.state.engine.dispose()
    assert target.exists()
