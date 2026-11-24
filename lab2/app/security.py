"""Хешування паролів і токени доступу (лише стандартна бібліотека).

Рішення, яких немає в ЛР1 (OPEN-C05, потребують підтвердження команди):
 - пароль: scrypt із випадковою сіллю;
 - токен: `<user_id>.<expires_at>.<HMAC-SHA256>`, чинний 24 години, без серверного відкликання (F-22).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

TOKEN_TTL_SECONDS = 24 * 60 * 60
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return "$".join(
        [
            "scrypt",
            str(_SCRYPT_N),
            str(_SCRYPT_R),
            str(_SCRYPT_P),
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        ]
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.scrypt(
            password.encode(), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def issue_token(
    user_id: int, secret: str, *, now: int | None = None, ttl: int = TOKEN_TTL_SECONDS
) -> str:
    expires_at = int(now if now is not None else time.time()) + ttl
    payload = f"{user_id}.{expires_at}"
    return f"{payload}.{_sign(payload, secret)}"


def verify_token(token: str, secret: str, *, now: int | None = None) -> int | None:
    """Повертає id користувача або None, якщо токен недійсний чи прострочений."""
    try:
        user_id_raw, expires_raw, signature = token.split(".")
        payload = f"{user_id_raw}.{expires_raw}"
        if not hmac.compare_digest(signature, _sign(payload, secret)):
            return None
        if int(expires_raw) <= int(now if now is not None else time.time()):
            return None
        return int(user_id_raw)
    except ValueError:
        return None
