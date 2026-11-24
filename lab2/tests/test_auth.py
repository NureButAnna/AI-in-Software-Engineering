"""Зріз A: реєстрація, вхід, токен (T01–T05, T22 для помилок автентифікації)."""

from __future__ import annotations

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import security
from app.models import User
from app.routes import current_user, router

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
VALID = {"email": "user@example.com", "password": "examplePass8"}


def count_users(app) -> int:
    with Session(app.state.engine) as db:
        return db.scalar(select(func.count()).select_from(User))


def assert_error(response, status, code):
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["details"], list)
    return error


# --- T01 ---------------------------------------------------------------------


def test_t01_register_valid_returns_201_without_secrets(client, app):
    response = client.post(REGISTER, json=VALID)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "created_at"}
    assert body["email"] == "user@example.com"
    assert body["created_at"].endswith("Z")
    assert "password" not in response.text and "hash" not in response.text
    assert count_users(app) == 1
    with Session(app.state.engine) as db:
        stored = db.scalar(select(User))
        assert stored.password_hash != VALID["password"]
        assert VALID["password"] not in stored.password_hash


def test_t01_register_does_not_log_user_in(client):
    response = client.post(REGISTER, json=VALID)
    assert "access_token" not in response.json()


def test_t01_email_is_trimmed_and_lowercased(client):
    response = client.post(REGISTER, json={"email": "  User@Example.COM ", "password": "examplePass8"})
    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"


# --- T02 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "", "password": "examplePass8"},
        {"email": "   ", "password": "examplePass8"},
        {"email": "not-an-email", "password": "examplePass8"},
        {"email": "a@b", "password": "examplePass8"},
        {"email": "user@example.com", "password": ""},
        {"email": "user@example.com", "password": "short7!"},
        {"email": "user@example.com", "password": "        "},
        {"email": "user@example.com"},
        {"password": "examplePass8"},
        {},
        {"email": 5, "password": "examplePass8"},
        {"email": "user@example.com", "password": 12345678},
        {"email": "user@example.com", "password": "examplePass8", "id": 1},
        {"email": "user@example.com", "password": "examplePass8", "password_hash": "x"},
    ],
)
def test_t02_register_invalid_input_is_422_and_creates_nothing(client, app, payload):
    response = client.post(REGISTER, json=payload)
    error = assert_error(response, 422, "VALIDATION_ERROR")
    assert error["details"], "очікується деталь поля"
    assert count_users(app) == 0


def test_t02_password_of_exactly_8_characters_is_accepted(client):
    response = client.post(REGISTER, json={"email": "u@example.com", "password": "12345678"})
    assert response.status_code == 201


@pytest.mark.parametrize("raw", ["[]", "null", "42", "not json"])
def test_t02_non_object_body_is_422(client, raw):
    response = client.post(REGISTER, content=raw, headers={"Content-Type": "application/json"})
    assert_error(response, 422, "VALIDATION_ERROR")


# --- T03 ---------------------------------------------------------------------


def test_t03_duplicate_email_is_409_case_insensitive(client, app):
    assert client.post(REGISTER, json=VALID).status_code == 201
    again = client.post(REGISTER, json={"email": "USER@example.com", "password": "anotherPass9"})
    assert_error(again, 409, "DUPLICATE_EMAIL")
    assert count_users(app) == 1


# --- T04 ---------------------------------------------------------------------


def test_t04_login_returns_working_bearer_token(client, app):
    client.post(REGISTER, json=VALID)
    response = client.post(LOGIN, json=VALID)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    user_id = security.verify_token(body["access_token"], app.state.secret_key)
    assert user_id is not None


def test_t04_wrong_password_and_unknown_email_give_same_401(client):
    client.post(REGISTER, json=VALID)
    wrong_password = client.post(LOGIN, json={**VALID, "password": "wrongPass99"})
    unknown_email = client.post(LOGIN, json={"email": "nobody@example.com", "password": "examplePass8"})
    assert_error(wrong_password, 401, "INVALID_CREDENTIALS")
    assert_error(unknown_email, 401, "INVALID_CREDENTIALS")
    assert wrong_password.json() == unknown_email.json()


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "", "password": "examplePass8"},
        {"email": "not-an-email", "password": "examplePass8"},
        {"email": "user@example.com", "password": ""},
        {"email": "user@example.com", "password": "   "},
        {"email": "user@example.com"},
        {"email": "user@example.com", "password": "examplePass8", "extra": 1},
    ],
)
def test_t04_login_invalid_input_is_422(client, payload):
    assert_error(client.post(LOGIN, json=payload), 422, "VALIDATION_ERROR")


def test_t04_login_is_case_insensitive_for_email(client):
    client.post(REGISTER, json=VALID)
    response = client.post(LOGIN, json={"email": "USER@Example.com", "password": "examplePass8"})
    assert response.status_code == 200


# --- T05 ---------------------------------------------------------------------


@pytest.fixture
def probe_client(app):
    """Тимчасовий захищений маршрут перевіряє залежність current_user без інших зрізів."""
    probe = APIRouter()
    probe.add_api_route("/api/v1/_probe", lambda user=Depends(current_user): {"id": user.id})
    app.include_router(probe)
    with TestClient(app) as test_client:
        yield test_client


def _token_for(client, app):
    client.post(REGISTER, json=VALID)
    return client.post(LOGIN, json=VALID).json()["access_token"]


def test_t05_valid_token_gives_access(probe_client, app):
    token = _token_for(probe_client, app)
    response = probe_client.get("/api/v1/_probe", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer garbage"},
        {"Authorization": "Basic dXNlcjpwYXNz"},
        {"Authorization": "Bearer 1.9999999999.deadbeef"},
    ],
)
def test_t05_missing_or_invalid_token_is_401(probe_client, headers):
    assert_error(probe_client.get("/api/v1/_probe", headers=headers), 401, "AUTH_REQUIRED")


def test_t05_expired_token_is_401(probe_client, app):
    probe_client.post(REGISTER, json=VALID)
    expired = security.issue_token(1, app.state.secret_key, now=1_000, ttl=60)
    response = probe_client.get("/api/v1/_probe", headers={"Authorization": f"Bearer {expired}"})
    assert_error(response, 401, "AUTH_REQUIRED")


def test_t05_token_signed_with_other_secret_is_401(probe_client):
    probe_client.post(REGISTER, json=VALID)
    forged = security.issue_token(1, "another-secret")
    response = probe_client.get("/api/v1/_probe", headers={"Authorization": f"Bearer {forged}"})
    assert_error(response, 401, "AUTH_REQUIRED")


def test_t05_token_of_deleted_user_is_401(probe_client, app):
    token = _token_for(probe_client, app)
    with Session(app.state.engine) as db:
        db.delete(db.scalar(select(User)))
        db.commit()
    response = probe_client.get("/api/v1/_probe", headers={"Authorization": f"Bearer {token}"})
    assert_error(response, 401, "AUTH_REQUIRED")


# --- security (модульні перевірки) ----------------------------------------------


def test_password_hash_is_salted_and_verifiable():
    first, second = security.hash_password("examplePass8"), security.hash_password("examplePass8")
    assert first != second
    assert security.verify_password("examplePass8", first)
    assert not security.verify_password("examplePass9", first)
    assert not security.verify_password("examplePass8", "garbage")


def test_token_roundtrip_and_expiry():
    token = security.issue_token(7, "s", now=1_000, ttl=60)
    assert security.verify_token(token, "s", now=1_059) == 7
    assert security.verify_token(token, "s", now=1_060) is None
    assert security.verify_token(token + "0", "s", now=1_000) is None


def test_router_prefix_is_api_v1():
    assert router.prefix == "/api/v1"
