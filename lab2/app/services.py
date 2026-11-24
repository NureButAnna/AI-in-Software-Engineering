"""Бізнес-правила. Не залежить від FastAPI; транзакціями керує сервіс."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import security
from app.errors import (
    DuplicateEmail,
    InvalidCredentials,
    InvalidStateTransition,
    NotFound,
)
from app.models import (
    TERMINAL_STATUSES,
    Case,
    CaseDocument,
    CaseInstitution,
    CaseStatus,
    Document,
    Institution,
    Reminder,
    Task,
    User,
    utcnow,
)
from app.sorting import case_sort_key, uk_key

# Хеш для вирівнювання часу відповіді, коли email невідомий.
_DUMMY_HASH = security.hash_password("not-a-real-password")


def register_user(db: Session, email: str, password: str) -> User:
    """US-01: новий користувач з унікальним email; автоматичного входу немає."""
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise DuplicateEmail()
    now = utcnow()
    user = User(
        email=email,
        password_hash=security.hash_password(password),
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateEmail() from None
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    """US-02: однакова помилка для невідомого email і хибного пароля."""
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        security.verify_password(password, _DUMMY_HASH)
        raise InvalidCredentials()
    if not security.verify_password(password, user.password_hash):
        raise InvalidCredentials()
    return user


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_case(db: Session, owner_id: int, title: str, deadline) -> Case:
    """US-03: нова справа завжди починається зі статусу PREPARING."""
    now = utcnow()
    case = Case(
        owner_id=owner_id,
        title=title,
        status=CaseStatus.PREPARING.value,
        deadline=deadline,
        created_at=now,
        updated_at=now,
    )
    db.add(case)
    db.commit()
    return case


def get_owned_case(db: Session, owner_id: int, case_id: int) -> Case:
    """Чужа й неіснуюча справа однаково дають NotFound (FR-02)."""
    case = db.get(Case, case_id)
    if case is None or case.owner_id != owner_id:
        raise NotFound()
    return case


def list_cases(db: Session, owner_id: int) -> list[Case]:
    """Лише власні справи у визначеному порядку; порожній список — не помилка."""
    cases = db.scalars(select(Case).where(Case.owner_id == owner_id)).all()
    return sorted(cases, key=case_sort_key)


def case_details(db: Session, case: Case) -> dict:
    """Справа з пов'язаними задачами, документами й установами (AC-04.7)."""
    tasks = db.scalars(
        select(Task).where(Task.case_id == case.id).order_by(Task.created_at, Task.id)
    ).all()
    documents = db.scalars(
        select(Document)
        .join(CaseDocument, CaseDocument.document_id == Document.id)
        .where(CaseDocument.case_id == case.id)
        .order_by(Document.created_at, Document.id)
    ).all()
    institutions = db.scalars(
        select(Institution)
        .join(CaseInstitution, CaseInstitution.institution_id == Institution.id)
        .where(CaseInstitution.case_id == case.id)
    ).all()
    institutions = sorted(institutions, key=lambda item: (uk_key(item.name), item.id))
    return {"tasks": tasks, "documents": documents, "institutions": institutions}


# Матриця переходів (lab1/docs/requirements.md, розділ 2.2): поточний → дозволені наступні.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "PREPARING": frozenset({"SUBMITTED", "CANCELLED"}),
    "SUBMITTED": frozenset({"PREPARING", "IN_REVIEW", "CANCELLED"}),
    "IN_REVIEW": frozenset({"APPROVED", "REJECTED", "CANCELLED"}),
    "APPROVED": frozenset(),
    "REJECTED": frozenset(),
    "CANCELLED": frozenset(),
}


def update_case(db: Session, case: Case, changes: dict) -> Case:
    """PATCH справи: усі передані поля вже перевірено схемою; запис — однією транзакцією."""
    if case.status in TERMINAL_STATUSES:
        # Заборонено навіть тоді, коли значення збігаються з поточними.
        raise InvalidStateTransition()
    changed = {key: value for key, value in changes.items() if getattr(case, key) != value}
    if not changed:
        return case  # updated_at не змінюється без фактичної зміни
    for key, value in changed.items():
        setattr(case, key, value)
    case.updated_at = utcnow()
    db.commit()
    return case


def change_status(db: Session, case: Case, new_status: str) -> Case:
    """Окрема операція зміни статусу за матрицею; повторення поточного статусу — успіх без змін."""
    if new_status == case.status:
        return case
    if new_status not in ALLOWED_TRANSITIONS[case.status]:
        raise InvalidStateTransition(f"Перехід {case.status} → {new_status} заборонений")
    case.status = new_status
    case.updated_at = utcnow()
    db.commit()
    return case


def delete_case(db: Session, case: Case) -> None:
    """Видалення однією транзакцією (US-03, розділ 5.2): задачі й зв'язки зникають через ON DELETE
    CASCADE, у нагадувань case_id стає NULL; документи, установи й нагадування лишаються."""
    db.execute(delete(Case).where(Case.id == case.id))
    db.commit()


def _is_overdue(case: Case, today: date) -> bool:
    return (
        case.deadline is not None
        and case.status not in TERMINAL_STATUSES
        and case.deadline < today
    )


def _is_upcoming(case: Case, today: date) -> bool:
    return (
        case.deadline is not None
        and case.status not in TERMINAL_STATUSES
        and today <= case.deadline <= today + timedelta(days=14)
    )


def dashboard(db: Session, owner_id: int, today: date) -> dict:
    """US-05, AC-10.3: лише читання; «сьогодні» передає клієнт."""
    cases = list_cases(db, owner_id)
    reminders = db.scalars(
        select(Reminder)
        .where(Reminder.owner_id == owner_id, Reminder.reminder_date <= today)
        .order_by(Reminder.reminder_date, Reminder.id)
    ).all()
    return {
        "overdue_cases": [c for c in cases if _is_overdue(c, today)],
        "upcoming_cases": [c for c in cases if _is_upcoming(c, today)],
        "due_reminders": list(reminders),
    }
