"""Доменні помилки. Тексти — з каталогу lab1/docs/requirements.md, розділ 4."""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    code = "DOMAIN_ERROR"
    message = "Помилка"

    def __init__(self, message: str | None = None, details: list[dict[str, Any]] | None = None):
        self.message = message or self.message
        self.details = details or []
        super().__init__(self.message)


class AuthRequired(DomainError):
    code = "AUTH_REQUIRED"
    message = "Потрібна автентифікація: токен відсутній або недійсний"


class InvalidCredentials(DomainError):
    code = "INVALID_CREDENTIALS"
    message = "Неправильний email або пароль"


class NotFound(DomainError):
    code = "NOT_FOUND"
    message = "Запис не знайдено"


class DuplicateEmail(DomainError):
    code = "DUPLICATE_EMAIL"
    message = "Користувач із таким email уже існує"


class InvalidStateTransition(DomainError):
    code = "INVALID_STATE_TRANSITION"
    message = "Операція заборонена для поточного статусу справи"


class ValidationFailed(DomainError):
    code = "VALIDATION_ERROR"
    message = "Некоректні вхідні дані"
