# PaperTrail — бекенд (ЛР2)

Локальний REST-сервіс (FastAPI + SQLite) за специфікацією ЛР1: `../lab1/docs/` (вимоги, контракт даних, `api-contract.md`).
Реалізовано **9 маршрутів** ЛР1 і технічний `GET /health`. Маршрути для задач, документів, файлів, установ і нагадувань
(реєстр API §5) та FR-08 у цій роботі **не реалізуються**. Сервіс призначений для локального запуску.

**Версія Python:** потрібен Python 3.11 або новіший (зафіксовані залежності не встановлюються на 3.10); розроблено й перевірено на Python 3.13.18 (Linux). Погодьте в команді єдину версію.

**ЛР3:** [звіт про тестування](docs/lab-03.md) та [артефакти й команди відтворення](reports/lr3/README.md).

## Чисте встановлення і запуск

```bash
cd lab2
python -m venv .venv
source .venv/bin/activate            # Windows cmd: .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
python -m uvicorn app.main:create_app --factory --host 127.0.0.1
```

Інтерактивна документація: http://127.0.0.1:8000/docs. База створюється в `data/app.db` (не комітиться); інший шлях задає
змінна `PAPERTRAIL_DB`. Без `PAPERTRAIL_SECRET_KEY` токени діють лише до перезапуску процесу.
Не прив'язуйте сервіс до публічного інтерфейсу.

## Перевірки

```bash
python -m pytest -q
python -m ruff check app tests --select E4,E7,E9,F,I
python -m bandit -q -r app           # необов'язково
python -m pytest -q --cov=app        # необов'язково
```

Кожен тест працює з власною файловою базою в `tmp_path`; робоча база `data/app.db` не використовується (сценарій T21).

## Приклад API

```bash
B=http://127.0.0.1:8000/api/v1
curl -s -X POST $B/auth/register -H 'Content-Type: application/json' -d '{"email":"me@example.com","password":"examplePass8"}'
TOKEN=$(curl -s -X POST $B/auth/login -H 'Content-Type: application/json' -d '{"email":"me@example.com","password":"examplePass8"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s -X POST $B/cases -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"title":"Паспорт","deadline":"2026-12-01"}'
curl -s -X PATCH $B/cases/1/status -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"status":"SUBMITTED"}'
curl -s "$B/cases?status=SUBMITTED&due=upcoming&today=2026-11-24" -H "Authorization: Bearer $TOKEN"
curl -s "$B/dashboard?today=2026-11-24" -H "Authorization: Bearer $TOKEN"
```

| Маршрут | Зріз | Тести |
|---|---|---|
| `POST /auth/register`, `POST /auth/login` | A | T01–T05 |
| `POST /cases`, `GET /cases`, `GET /cases/{id}` | B | T06–T09 |
| `PATCH /cases/{id}`, `PATCH /cases/{id}/status` | C | T10–T13 |
| `DELETE /cases/{id}`, `GET /dashboard` | D | T14–T16 |
| фільтри `status`, `due`, `today` у `GET /cases` | E | T17–T19 |
| `GET /health`; форма помилок; ізоляція БД; перезапуск | — | T20–T22 |

## Структура

```
.agents/skills/papertrail-slice/   Skill (SKILL.md, references/slices.md) — у корені репозиторію
.claude/skills/papertrail-slice    символьне посилання для Claude Code (шукає Skills у .claude/skills/)
lab2/app/        main.py (create_app), routes.py, schemas.py, services.py, models.py, database.py,
                 security.py, sorting.py, predicates.py, errors.py
lab2/tests/      conftest.py + тести за зрізами
lab2/docs/       lab-02.md (звіт), experiment-lr2.csv, ai-log.md, traceability.csv
```

## Навчальні обмеження та рішення, яких немає в ЛР1

- Формат токена, TTL (24 год) і хешування пароля (scrypt) — робочі рішення; потребують підтвердження (OPEN-C05).
- `GET /health` — технічний маршрут; `api-contract.md` вимагає окремо погодити такий маршрут.
- Фільтрація й сортування списку справ виконуються в Python над прочитаними записами (достатньо для малого обсягу).
- Максимальні довжини полів не задані специфікацією й не обмежуються.
- AI-витягування (ЛР4), файли документів, задачі, установи, нагадування (CRUD) — поза межами ЛР2.
