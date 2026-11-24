"""Схеми запитів і відповідей: форма даних до виклику бізнес-логіки."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    ValidationError,
)

from app.errors import ValidationFailed

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_MESSAGES = {
    "missing": "Поле обов'язкове",
    "extra_forbidden": "Невідоме або нередаговане поле",
    "string_type": "Очікується рядок",
    "dict_type": "Очікується JSON-об'єкт",
    "model_type": "Очікується JSON-об'єкт",
}


def parse_iso_date(value: Any) -> date | None:
    """Строга дата YYYY-MM-DD; None залишається None."""
    if value is None:
        return None
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise ValueError("Очікується дата у форматі YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("Некоректна календарна дата") from None


def format_timestamp(value: datetime) -> str:
    """UTC ISO 8601 із суфіксом Z (NFR-06)."""
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _details_from(exc: ValidationError) -> list[dict[str, str]]:
    details = []
    for err in exc.errors():
        field = ".".join(str(part) for part in err["loc"]) or "body"
        if err["type"] == "value_error":
            message = str(err["ctx"]["error"])
        else:
            message = _MESSAGES.get(err["type"], err["msg"])
        details.append({"field": field, "message": message})
    return details


def validate(model: type[BaseModel], payload: Any) -> Any:
    """Валідує тіло запиту; будь-яка помилка → ValidationFailed (без часткових змін)."""
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ValidationFailed(details=_details_from(exc)) from None


class _Strict(BaseModel):
    # Невідомі поля заборонені, типи строгі: "5" не стає числом, "true" — булевим.
    model_config = ConfigDict(extra="forbid", strict=True)


def _normalize_email(value: str) -> str:
    value = value.strip().lower()
    if not value:
        raise ValueError("Email не може бути порожнім")
    if not _EMAIL_RE.fullmatch(value):
        raise ValueError("Некоректний формат email")
    return value


Email = Annotated[str, AfterValidator(_normalize_email)]


def _new_password(value: str) -> str:
    if not value.strip():
        raise ValueError("Пароль не може бути порожнім або лише з пробілів")
    if len(value) < 8:
        raise ValueError("Пароль має містити щонайменше 8 символів")
    return value


def _login_password(value: str) -> str:
    if not value.strip():
        raise ValueError("Пароль не може бути порожнім або лише з пробілів")
    return value


class RegisterRequest(_Strict):
    email: Email
    password: Annotated[str, AfterValidator(_new_password)]


class LoginRequest(_Strict):
    email: Email
    password: Annotated[str, AfterValidator(_login_password)]


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _non_empty_trimmed(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Назва не може бути порожньою")
    return value


Title = Annotated[str, AfterValidator(_non_empty_trimmed)]
Deadline = Annotated[date | None, BeforeValidator(parse_iso_date)]


class CaseCreate(_Strict):
    title: Title
    deadline: Deadline = None


class CaseResponse(BaseModel):
    id: int
    title: str
    status: str
    deadline: date | None
    created_at: str
    updated_at: str

    @classmethod
    def from_case(cls, case) -> CaseResponse:
        return cls(
            id=case.id,
            title=case.title,
            status=case.status,
            deadline=case.deadline,
            created_at=format_timestamp(case.created_at),
            updated_at=format_timestamp(case.updated_at),
        )


class TaskItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    is_completed: bool


class DocumentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    received_date: date


class InstitutionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CaseDetailsResponse(CaseResponse):
    tasks: list[TaskItem]
    documents: list[DocumentItem]
    institutions: list[InstitutionItem]
