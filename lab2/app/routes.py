"""HTTP-шар: токен → користувач, виклик сервісу, доменна помилка → відповідь."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, FastAPI, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import schemas, security, services
from app.errors import (
    AuthRequired,
    DomainError,
    DuplicateEmail,
    InvalidCredentials,
    InvalidStateTransition,
    NotFound,
    ValidationFailed,
)
from app.models import User

router = APIRouter(prefix="/api/v1")
_bearer = HTTPBearer(auto_error=False)

_HTTP_STATUS: dict[type[DomainError], int] = {
    AuthRequired: 401,
    InvalidCredentials: 401,
    NotFound: 404,
    DuplicateEmail: 409,
    InvalidStateTransition: 409,
    ValidationFailed: 422,
}


def _error_response(status: int, code: str, message: str, details: list | None = None):
    body = {"error": {"code": code, "message": message, "details": details or []}}
    return JSONResponse(status_code=status, content=body)


def install_error_handlers(app: FastAPI) -> None:
    """Єдина форма помилок: {"error": {"code", "message", "details"}}."""

    @app.exception_handler(DomainError)
    async def _domain(_request: Request, exc: DomainError):
        status = _HTTP_STATUS.get(type(exc), 400)
        return _error_response(status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _request_validation(_request: Request, exc: RequestValidationError):
        details = [
            {
                "field": ".".join(str(p) for p in err["loc"] if p not in ("body", "path", "query")),
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return _error_response(422, "VALIDATION_ERROR", ValidationFailed.message, details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return _error_response(404, NotFound.code, NotFound.message)
        return _error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))

    @app.exception_handler(Exception)
    async def _unexpected(_request: Request, _exc: Exception):
        # Без SQL, traceback і локальних шляхів у відповіді.
        return _error_response(500, "INTERNAL_ERROR", "Внутрішня помилка сервера")


def get_db(request: Request):
    with request.app.state.session_factory() as db:
        yield db


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AuthRequired()
    user_id = security.verify_token(credentials.credentials, request.app.state.secret_key)
    user = services.get_user(db, user_id) if user_id is not None else None
    if user is None:
        raise AuthRequired()
    return user


@router.post("/auth/register", status_code=201, response_model=schemas.UserResponse, tags=["auth"])
def register(payload: dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    data = schemas.validate(schemas.RegisterRequest, payload)
    user = services.register_user(db, data.email, data.password)
    return schemas.UserResponse(
        id=user.id, email=user.email, created_at=schemas.format_timestamp(user.created_at)
    )


@router.post("/auth/login", response_model=schemas.TokenResponse, tags=["auth"])
def login(
    request: Request, payload: dict[str, Any] = Body(...), db: Session = Depends(get_db)
):
    data = schemas.validate(schemas.LoginRequest, payload)
    user = services.authenticate(db, data.email, data.password)
    token = security.issue_token(user.id, request.app.state.secret_key)
    return schemas.TokenResponse(access_token=token)


@router.post("/cases", status_code=201, response_model=schemas.CaseResponse, tags=["cases"])
def create_case(
    payload: dict[str, Any] = Body(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    data = schemas.validate(schemas.CaseCreate, payload)
    case = services.create_case(db, user.id, data.title, data.deadline)
    return schemas.CaseResponse.from_case(case)


@router.get("/cases", response_model=list[schemas.CaseResponse], tags=["cases"])
def list_cases(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [schemas.CaseResponse.from_case(c) for c in services.list_cases(db, user.id)]


@router.get("/cases/{case_id}", response_model=schemas.CaseDetailsResponse, tags=["cases"])
def get_case(
    case_id: int = Path(gt=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    case = services.get_owned_case(db, user.id, case_id)
    related = services.case_details(db, case)
    return schemas.CaseDetailsResponse(
        **schemas.CaseResponse.from_case(case).model_dump(), **related
    )
