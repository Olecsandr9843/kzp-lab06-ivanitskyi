"""Завантаження CSV і перетворення рядків на об'єкти моделі.

Тут — єдине місце, де текст із файла стає об'єктом: loader розбирає формат (число, ціле,
логічне значення), а предметні правила (невід'ємність, непорожні назви) перевіряють
конструктор і setter-и :class:`~kzp_lab07.models.Medicine`.
"""

import csv
from collections.abc import Iterator
from pathlib import Path

from .errors import DataError
from .models import Medicine, create_medicine

#: Обов'язкові стовпці CSV (той самий формат, що й у ЛР6).
FIELDS: tuple[str, ...] = ("name", "form", "price", "days_left", "prescription")
TRUE_VALUES = frozenset({"true", "yes", "так", "1"})
FALSE_VALUES = frozenset({"false", "no", "ні", "0"})


def iter_medicines(path: Path) -> Iterator[Medicine]:
    """Читає CSV по одному рядку й видає об'єкти препаратів (генератор).

    Args:
        path: шлях до CSV-файла із заголовком ``name,form,price,days_left,prescription``.

    Yields:
        Об'єкти :class:`PrescriptionMedicine` або :class:`FreeMedicine` у порядку файла.

    Raises:
        DataError: файл не читається, порожній, заголовок неповний або значення хибне;
            повідомлення містить номер рядка й назву поля.
    """
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            _check_header(reader.fieldnames)
            for row in reader:
                yield _to_medicine(row, reader.line_num)
    except OSError as error:
        raise DataError(f"не вдалося прочитати файл {path}: {error.strerror or error}") from error
    except csv.Error as error:
        raise DataError(f"пошкоджений CSV у файлі {path}: {error}") from error


def load_medicines(path: Path) -> list[Medicine]:
    """Читає весь CSV у список об'єктів.

    Args:
        path: шлях до CSV-файла.

    Returns:
        Список об'єктів; порожній, якщо після заголовка немає рядків.

    Raises:
        DataError: див. :func:`iter_medicines`.
    """
    return list(iter_medicines(path))


def _to_medicine(row: dict, line: int) -> Medicine:
    """Перетворює рядок ``DictReader`` на об'єкт, доповнюючи помилки номером рядка."""
    if None in row:
        raise DataError(f"рядок {line}: зайві значення {row[None]}")
    name = _raw(row, "name", line)
    form = _raw(row, "form", line)
    price = _parse(row, "price", line, float, "число з крапкою")
    days_left = _parse(row, "days_left", line, int, "ціле число")
    prescription = _flag(row, "prescription", line)
    try:
        return create_medicine(name, form, price, days_left, prescription)
    except (TypeError, ValueError) as error:
        # Повідомлення setter-а вже називає поле; додаємо лише номер рядка.
        raise DataError(f"рядок {line}, {error}") from error


def _check_header(fieldnames: list[str] | None) -> None:
    """Перевіряє, що CSV має заголовок з усіма обов'язковими стовпцями."""
    if fieldnames is None:
        raise DataError("порожній CSV: немає рядка заголовка")
    missing = [field for field in FIELDS if field not in fieldnames]
    if missing:
        raise DataError(f"відсутні стовпці: {', '.join(missing)}")


def _raw(row: dict, field: str, line: int) -> str:
    """Текст поля без пробілів по краях; відсутнє чи порожнє значення — помилка."""
    value = row.get(field)
    if value is None:
        raise DataError(f"рядок {line}, поле «{field}»: значення відсутнє")
    value = value.strip()
    if not value:
        raise DataError(f"рядок {line}, поле «{field}»: порожнє значення")
    return value


def _parse(row: dict, field: str, line: int, kind: type, expected: str):
    """Перетворює текст на число типу ``kind``; хибний формат — помилка з першопричиною."""
    text = _raw(row, field, line)
    try:
        return kind(text)
    except ValueError as error:
        raise DataError(
            f"рядок {line}, поле «{field}»: очікується {expected}, отримано {text!r}"
        ) from error


def _flag(row: dict, field: str, line: int) -> bool:
    """Логічне поле: true/false, yes/no, так/ні, 1/0 без урахування регістру."""
    text = _raw(row, field, line).lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise DataError(f"рядок {line}, поле «{field}»: очікується true або false, отримано {text!r}")
