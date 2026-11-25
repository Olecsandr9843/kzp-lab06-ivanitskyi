"""Завантаження CSV і перетворення рядків на типізовані записи."""

import csv
import math
from collections.abc import Iterator
from pathlib import Path
from typing import TypedDict

from .errors import DataError

#: Обов'язкові стовпці CSV у порядку заголовка.
FIELDS: tuple[str, ...] = ("name", "form", "price", "days_left", "prescription")

#: Допустимі тексти для логічного поля prescription (після нормалізації).
TRUE_VALUES = frozenset({"true", "yes", "так", "1"})
FALSE_VALUES = frozenset({"false", "no", "ні", "0"})


class Medicine(TypedDict):
    """Типізований запис про препарат."""

    name: str
    form: str
    price: float
    days_left: int
    prescription: bool


def iter_records(path: Path) -> Iterator[Medicine]:
    """Читає CSV по одному рядку й видає перевірені записи (генератор).

    Файл відкривається через ``with`` з ``encoding="utf-8"`` і ``newline=""``: модуль
    ``csv`` сам розпізнає роздільники рядків і перенесення всередині лапок. У пам'яті
    одночасно перебуває лише один рядок, тому функція придатна й для великих файлів.

    Args:
        path: шлях до CSV-файла із заголовком ``name,form,price,days_left,prescription``.

    Yields:
        Записи з полями потрібних типів у порядку файла.

    Raises:
        DataError: файл не читається, порожній, заголовок неповний або значення хибне.
    """
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            _check_header(reader.fieldnames)
            # Рядок 1 — заголовок, тому записи нумеруються з 2, як у текстовому редакторі.
            for row in reader:
                yield parse_row(row, reader.line_num)
    except OSError as error:
        raise DataError(f"не вдалося прочитати файл {path}: {error.strerror or error}") from error
    except csv.Error as error:
        raise DataError(f"пошкоджений CSV у файлі {path}: {error}") from error


def load_records(path: Path) -> list[Medicine]:
    """Читає весь CSV у список записів.

    Args:
        path: шлях до CSV-файла.

    Returns:
        Список записів; порожній, якщо після заголовка немає рядків.

    Raises:
        DataError: див. :func:`iter_records`.
    """
    return list(iter_records(path))


def parse_row(row: dict[str | None, str | list[str] | None], line: int) -> Medicine:
    """Перетворює один рядок ``DictReader`` на типізований запис.

    Args:
        row: словник «стовпець → текст» від ``csv.DictReader``.
        line: номер рядка у файлі для повідомлення про помилку.

    Returns:
        Перевірений запис.

    Raises:
        DataError: рядок має зайві або відсутні значення, число хибне чи від'ємне.
    """
    if None in row:
        # DictReader кладе зайві значення під ключ None.
        raise DataError(f"рядок {line}: зайві значення {row[None]}")
    name = _text(row, "name", line)
    form = _text(row, "form", line).lower()
    price = _number(row, "price", line, float)
    days_left = _number(row, "days_left", line, int)
    prescription = _flag(row, "prescription", line)
    return Medicine(
        name=name, form=form, price=price, days_left=days_left, prescription=prescription
    )


def _check_header(fieldnames: list[str] | None) -> None:
    """Перевіряє, що CSV має заголовок з усіма обов'язковими стовпцями."""
    if fieldnames is None:
        raise DataError("порожній CSV: немає рядка заголовка")
    missing = [field for field in FIELDS if field not in fieldnames]
    if missing:
        raise DataError(f"відсутні стовпці: {', '.join(missing)}")


def _raw(row: dict, field: str, line: int) -> str:
    """Повертає текст поля без пробілів по краях; відсутнє чи порожнє значення — помилка."""
    value = row.get(field)
    if value is None:
        # DictReader підставляє None, якщо в рядку менше значень, ніж стовпців.
        raise DataError(f"рядок {line}, поле «{field}»: значення відсутнє")
    value = value.strip()
    if not value:
        raise DataError(f"рядок {line}, поле «{field}»: порожнє значення")
    return value


def _text(row: dict, field: str, line: int) -> str:
    """Текстове поле: обрізає пробіли й нормалізує внутрішні пробіли до одного."""
    return " ".join(_raw(row, field, line).split())


def _number(row: dict, field: str, line: int, kind: type[int] | type[float]) -> int | float:
    """Числове поле: перетворює через ``kind`` і перевіряє, що значення скінченне й ≥ 0."""
    text = _raw(row, field, line)
    try:
        value = kind(text)
    except ValueError as error:
        expected = "ціле число" if kind is int else "число з крапкою"
        raise DataError(
            f"рядок {line}, поле «{field}»: очікується {expected}, отримано {text!r}"
        ) from error
    if not math.isfinite(value) or value < 0:
        raise DataError(
            f"рядок {line}, поле «{field}»: значення має бути невід'ємним, отримано {text!r}"
        )
    return value


def _flag(row: dict, field: str, line: int) -> bool:
    """Логічне поле: приймає true/false, yes/no, так/ні, 1/0 без урахування регістру."""
    text = _raw(row, field, line).lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise DataError(f"рядок {line}, поле «{field}»: очікується true або false, отримано {text!r}")
