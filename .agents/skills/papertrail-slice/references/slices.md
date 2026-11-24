# Зрізи PaperTrail (Release MVP, 9 маршрутів ЛР1 + технічний GET /health)

Розділи вказано за lab1/docs/requirements.md («Контракт даних і бізнес-правил», далі КД)
і lab1/docs/api-contract.md (далі API). Код — у lab2/app/, тести — у lab2/tests/.
Усі маршрути, крім register і login, потребують токена.

## A. Облікові записи й токен
- Код (app/): schemas.py, services.py, routes.py, models.py, database.py, security.py, errors.py
- Тести (tests/): conftest.py, test_auth.py
- Читати: API — API-01, API-02, §1.1–1.2; КД — §1.1 (users)
- Критерії: AC-01.1–01.7, AC-02.1–02.4
- Сценарії: T01, T02, T03, T04, T05

## B. Створення й читання справ
- Код (app/): schemas.py, services.py, routes.py, models.py, sorting.py
- Тести (tests/): test_cases.py
- Читати: API — API-04, API-05 (без query), API-06; КД — §1.2 (cases), §5.3
- Критерії: AC-03.1–03.3, AC-04.1–04.8, AC-02.5
- Сценарії: T06, T07, T08, T09

## C. Зміни й статуси
- Код (app/): schemas.py, services.py, routes.py
- Тести (tests/): test_case_updates.py
- Читати: API — API-07, API-08, §1.3; КД — §2.2 (матриця переходів)
- Критерії: AC-03.8, AC-06.1–06.4
- Сценарії: T10, T11, T12, T13

## D. Видалення й дашборд
- Код (app/): services.py, routes.py, schemas.py
- Тести (tests/): test_delete_dashboard.py
- Читати: API — API-09, API-10; КД — §5.2, §5.4
- Критерії: AC-03.4–03.7, AC-05.1–05.3, AC-10.3
- Сценарії: T14, T15, T16

## E. Фільтри списку справ
- Код (app/): predicates.py, services.py, routes.py
- Тести (tests/): test_filters.py, test_predicates.py
- Читати: API — API-05 (query status, due, today); КД — §5.4, §5.5
- Критерії: AC-04.9
- Сценарії: T17, T18, T19

## Наскрізні сценарії (не прив'язані до одного зрізу)
- T20 — дані переживають перезапуск (повторний create_app на тому самому файлі БД)
- T21 — тести не торкаються робочої бази data/app.db
- T22 — єдина форма помилок {"error": {code, message, details}}, без SQL і traceback
