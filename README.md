# Аптека — звіт з CSV (Python)

Лабораторні роботи № 6–7 з курсу «Кросплатформні засоби програмування», варіант 11.
Автор: Іваницький. Поточна версія — **1.1.0** (ЛР7). Звіти: [REPORT.md](REPORT.md) (ЛР7),
[docs/REPORT-lab06.md](docs/REPORT-lab06.md) (ЛР6).

Дистрибутив `kzp-pharmacy` містить два пакети з однаковим зовнішнім звітом:

- `kzp_lab06` (команда `kzp-lab06`) — ЛР6, записи-словники;
- `kzp_lab07` (команда `kzp-lab07`) — ЛР7, об'єктна модель.

## Призначення

Програма читає CSV з асортиментом аптеки, перетворює поля на типізовані значення,
перевіряє дані та записує детермінований текстовий звіт:

- препарати з терміном придатності ≤ 30 днів (відбір);
- кількість препаратів за формою випуску (словник);
- множина форм випуску;
- найближчий термін придатності та середня ціна.

Вхідний файл не змінюється, звіт пишеться в окремий файл.

## Формат CSV

UTF-8, роздільник — кома, перший рядок — заголовок. Поля в лапках можуть містити кому й
подвоєні лапки.

```text
name,form,price,days_left,prescription
Парацетамол,таблетки,45.50,365,false
"Мазь ""Левомеколь"", 40 г",мазь,89.75,14,false
```

| Стовпець | Тип після перетворення | Правило |
|----------|------------------------|---------|
| `name` | `str` | непорожній; пробіли нормалізуються |
| `form` | `str` | непорожній; нижній регістр (`Таблетки` → `таблетки`) |
| `price` | `float` | скінченне число ≥ 0 |
| `days_left` | `int` | ціле ≥ 0 |
| `prescription` | `bool` | `true/false`, `yes/no`, `так/ні`, `1/0` (регістр не важливий) |

Файл лише із заголовком дає порожній звіт. Файл без заголовка, відсутній стовпець, порожнє
чи хибне значення спричиняють `DataError` з номером рядка й назвою поля.

## Встановлення

Потрібен Python 3.11 або новіший.

Windows (PowerShell або cmd):

```text
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

macOS / Ubuntu:

```text
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Якщо PowerShell забороняє активацію скриптів, можна викликати `.venv\Scripts\python.exe`
напряму, без активації.

## Запуск

```text
kzp-lab07 data/input.csv reports/summary.txt
python -m kzp_lab07.cli data/input.csv reports/summary.txt
kzp-lab07 data/input.csv reports/summary.txt --threshold 14
kzp-lab07 data/input.csv reports/summary.txt --details
kzp-lab07 --version
kzp-lab06 data/input.csv reports/summary-06.txt
```

`--details` (лише ЛР7) додає наприкінці оцінку доступності кожного препарату, середню оцінку
й трійку найдоступніших.

Коди завершення: `0` — успіх, `1` — помилка даних або файла (повідомлення в stderr),
`2` — хибні аргументи (наприклад, вхідний файл збігається з файлом звіту).

## Приклад звіту

```text
Звіт аптеки (варіант 11)
Вхідний файл: input.csv
Записів: 11
Середня ціна: 144.63 грн
Найближчий термін придатності: Мелоксикам (розчин) — 0 дн.
Рецептурних препаратів: 5
Термін придатності ≤ 30 дн.: 6
  Мелоксикам (розчин): 0 дн.
  Парацетамол (таблетки): 7 дн.
  Мазь "Левомеколь", 40 г (мазь): 14 дн.
  Назол (спрей): 14 дн.
  Інсулін (розчин): 20 дн.
  Цетиризин (таблетки): 30 дн.
Форми випуску (6): капсули, мазь, розчин, спрей, суспензія, таблетки
Кількість за формою:
  капсули: 1
  мазь: 1
  розчин: 2
  спрей: 1
  суспензія: 1
  таблетки: 5
Сумарна вартість асортименту: 1590.95
```

## Перевірки

```text
python -m pytest
ruff check .
ruff format --check .
python -m build --wheel
```

Перевірка wheel в окремому чистому середовищі:

```text
python -m venv .venv-wheel
.venv-wheel\Scripts\python -m pip install --no-deps dist\kzp_pharmacy-1.1.0-py3-none-any.whl
.venv-wheel\Scripts\python -m kzp_lab07.cli data\input.csv reports\wheel-summary.txt
```

У macOS та Ubuntu замість `.venv-wheel\Scripts\python` — `.venv-wheel/bin/python`.

## Об'єктна модель (ЛР7)

```text
              Medicine (ABC)                    Protocol Scored
    name, form — лише читання                   name, days_left,
    price, days_left — @property + setter       availability_score()
    __str__ __repr__ __eq__ __hash__ sort_key
    abstract availability_score()
           ┌──────────┴──────────┐
PrescriptionMedicine        FreeMedicine
max(10, 60 − штраф)    100 − штраф (− 20, якщо < 30 дн.)

@dataclass(frozen=True) Summary — незмінний підсумок аналізу
```

Штраф за ціну — 1 бал за кожні повні 10 грн, не більше 50. Препарат, термін якого спливає
сьогодні, отримує 0. Функції `analysis` працюють з будь-яким об'єктом протоколу `Scored` і не
перевіряють конкретний клас.

## Структура

```text
src/kzp_lab06/  — ЛР6 (словники): errors, loader, analysis, reporting, cli
src/kzp_lab07/  — ЛР7 (об'єкти):
  models.py     — Medicine, PrescriptionMedicine, FreeMedicine, Protocol Scored, Summary
  loader.py     — CSV → об'єкти, DataError з номером рядка
  analysis.py   — відбір, підсумок, середня доступність через протокол
  reporting.py  — звіт як у ЛР6, розділ --details, контекстний менеджер atomic_writer
  errors.py, cli.py, __main__.py
tests/          — pytest (test_*.py — ЛР6, test_lab07_*.py — ЛР7)
data/input.csv  — вхідні дані варіанта
reports/        — звіти (не в git)
docs/           — звіт ЛР6
tools/memory_benchmark.py — вимірювання пам'яті (ЛР6, зірочка)
ai/             — ролі ШІ-агентів
.github/        — CI, форми Issues, шаблон PR
```
