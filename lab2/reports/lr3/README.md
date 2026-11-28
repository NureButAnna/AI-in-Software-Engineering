# Артефакти експерименту ЛР3

Підсумок: [`lab-03.md`](../../docs/lab-03.md); метадані прогонів: [`mutation-matrix.csv`](mutation-matrix.csv). Команди Python виконуються з `lab2/` у віртуальному середовищі з `requirements-lock.txt`. Git-команди нижче виконуються з кореня репозиторію.

## R0 й обидва набори

Джерело R0 і T0 — `cbf5087`; джерело T1 — `02d5198`. Для T0 використайте чисту копію R0. Для T1 перенесіть тільки `tests/` командою `git restore --source=02d5198 --worktree -- lab2/tests`. У тому самому середовищі й каталозі `lab2/` виконайте:

```sh
mkdir -p reports/lr3
python -m pytest -q
# Для T1 замініть t0 на t1 в імені вихідного файлу.
python -m pytest --cov=app --cov-branch --cov-report=term-missing --cov-report=json:reports/lr3/coverage-t0.json
python -m bandit -r app -f json -o reports/lr3/bandit-r0.json
```

## Мутації й виправлення

| Копія | Коміт | Патч від батьківського коміту |
|---|---|---|
| M1 | `38cbaa27e72c41d6823e00982326a48ea319d08f` | [`m1.patch`](m1.patch) від R0 |
| M2 | `0422a09ac2df18f3be92f5115d8b6dccd716564d` | [`m2.patch`](m2.patch) від R0 |
| M3 | `942b1430c8d0a6833ffaeb711ac8681e1bca6684` | [`m3.patch`](m3.patch) від R0 |
| M1 fixed | `71cbafaf13df616a38a7dac6c2aa33505d3697cc` | [`m1-fix.patch`](m1-fix.patch) від M1 |
| M3 fixed | `c202d79ae336d7daea0f702ee89eb40082860012` | [`m3-fix.patch`](m3-fix.patch) від M3 |

Якщо локальних експериментальних гілок немає, створіть незалежні копії R0 (`git worktree add --detach <каталог> cbf5087`) і застосуйте відповідний патч із кореня копії: `git apply --unidiff-zero <повний-шлях-до-патча>`. Патчі збережено без контексту; застосовуйте їх тільки до зазначеної бази. Перед кожним T0/T1 перевірте, що версія `app/` та сама. З `lab2/`:

```sh
# Підставте m1, m2 або m3 в окремій копії; шлях веде до фінального checkout.
PYTHONPATH=. python /path/to/final-checkout/lab2/experiment/lr3_probe.py m1
python -m pytest -q --tb=short -o enable_assertion_pass_hook=false
```

Після T0 перенесіть T1 тим самим `git restore` і повторіть pytest. Для M1/M3 застосуйте відповідний патч виправлення, збережіть ті самі тести, повторіть контрольний запит, цільовий тест із матриці та двічі повний T1 (`python -m pytest -q`). У M3 і M3 fixed повторіть команду Bandit, змінивши ім’я файлу на `bandit-m3.json` і `bandit-m3-fixed.json` відповідно. Із фінальної інтеграційної версії запустіть `python -m pytest -q` і `python -m ruff check app tests --select E4,E7,E9,F,I`.
