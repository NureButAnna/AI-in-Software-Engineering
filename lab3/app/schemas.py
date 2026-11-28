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
    field_validator,
    model_validator,
)

from app.errors import ValidationFailed
from app.models import CaseStatus

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


class CasePatch(_Strict):
    """Часткове редагування: відсутнє поле — не змінювати, null лише для deadline."""

    title: Title | None = None
    deadline: Deadline = None

    @field_validator("title", mode="before")
    @classmethod
    def _title_is_not_nullable(cls, value):
        if value is None:
            raise ValueError("Назва є обов'язковою і не може бути null")
        return value

    @model_validator(mode="after")
    def _body_is_not_empty(self):
        if not self.model_fields_set:
            raise ValueError("Тіло запиту не може бути порожнім")
        return self


_STATUS_VALUES = [status.value for status in CaseStatus]


class StatusChange(_Strict):
    status: str

    @field_validator("status")
    @classmethod
    def _known_status(cls, value: str) -> str:
        if value not in _STATUS_VALUES:
            raise ValueError("Невідомий статус; допустимі: " + ", ".join(_STATUS_VALUES))
        return value


class ReminderItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reminder_date: date
    text: str
    case_id: int | None


class DashboardResponse(BaseModel):
    overdue_cases: list[CaseResponse]
    upcoming_cases: list[CaseResponse]
    due_reminders: list[ReminderItem]


def parse_today(query_params: Any, *, required: bool = True) -> date | None:
    """Параметр today=YYYY-MM-DD; невідомі параметри запиту заборонені."""
    details = [
        {"field": name, "message": "Невідомий параметр запиту"}
        for name in sorted({key for key, _ in query_params.multi_items()} - {"today"})
    ]
    values = query_params.getlist("today")
    today = None
    if len(values) > 1:
        details.append({"field": "today", "message": "Параметр today задається один раз"})
    elif values:
        try:
            today = parse_iso_date(values[0])
        except ValueError as exc:
            details.append({"field": "today", "message": str(exc)})
    elif required:
        details.append({"field": "today", "message": "Параметр today обов'язковий"})
    if details:
        raise ValidationFailed(details=details)
    return today


_DUE_VALUES = ("overdue", "upcoming")


def parse_cases_query(query_params: Any) -> tuple[str | None, str | None, date | None]:
    """GET /cases: status, due, today (усі необов'язкові); due потребує today; невідоме — 422."""
    details = [
        {"field": name, "message": "Невідомий параметр запиту"}
        for name in sorted({key for key, _ in query_params.multi_items()} - {"status", "due", "today"})
    ]
    single: dict[str, str | None] = {}
    for name in ("status", "due", "today"):
        values = query_params.getlist(name)
        if len(values) > 1:
            details.append({"field": name, "message": "Параметр задається один раз"})
        single[name] = values[0] if values else None

    status, due = single["status"], single["due"]
    if status is not None and status not in _STATUS_VALUES:
        details.append({"field": "status", "message": "Невідомий статус; допустимі: " + ", ".join(_STATUS_VALUES)})
    if due is not None and due not in _DUE_VALUES:
        details.append({"field": "due", "message": "Допустимі значення: overdue, upcoming"})
    today = None
    if single["today"] is not None:
        try:
            today = parse_iso_date(single["today"])
        except ValueError as exc:
            details.append({"field": "today", "message": str(exc)})
    elif due is not None:
        details.append({"field": "today", "message": "Параметр today обов'язковий разом із due"})
    if details:
        raise ValidationFailed(details=details)
    return status, due, today
