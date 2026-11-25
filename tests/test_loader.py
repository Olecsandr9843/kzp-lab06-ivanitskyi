"""Тести завантаження й перетворення CSV."""

from pathlib import Path

import pytest

from kzp_lab06.errors import DataError
from kzp_lab06.loader import iter_records, load_records


def test_loads_sample_with_types(sample_path: Path) -> None:
    """Контрольний файл: 11 записів, поля перетворено на потрібні типи."""
    records = load_records(sample_path)

    assert len(records) == 11
    first = records[0]
    assert first == {
        "name": "Парацетамол",
        "form": "таблетки",
        "price": 45.5,
        "days_left": 365,
        "prescription": False,
    }
    assert isinstance(first["price"], float)
    assert isinstance(first["days_left"], int)


def test_quoted_field_with_comma_and_quotes(sample_path: Path) -> None:
    """Кома й подвоєні лапки в полі в лапках розбираються модулем csv коректно."""
    names = [record["name"] for record in load_records(sample_path)]

    assert 'Мазь "Левомеколь", 40 г' in names


def test_text_is_normalized(write_csv) -> None:
    """Пробіли по краях і зайві пробіли всередині прибираються, форма — у нижньому регістрі."""
    path = write_csv("  Сироп   від кашлю ,  СИРОП ,10,5,TRUE\n")

    record = load_records(path)[0]

    assert record["name"] == "Сироп від кашлю"
    assert record["form"] == "сироп"
    assert record["prescription"] is True


@pytest.mark.parametrize(
    ("text", "expected"), [("true", True), ("Так", True), ("1", True), ("no", False)]
)
def test_prescription_accepts_several_spellings(write_csv, text: str, expected: bool) -> None:
    """Логічне поле приймає кілька написань."""
    assert load_records(write_csv(f"А,мазь,1,1,{text}\n"))[0]["prescription"] is expected


def test_header_only_gives_empty_list(write_csv) -> None:
    """Правило порожнього входу: лише заголовок — порожній список, не помилка."""
    assert load_records(write_csv("")) == []


def test_completely_empty_file_is_error(write_csv) -> None:
    """Файл без заголовка — помилка."""
    with pytest.raises(DataError, match="немає рядка заголовка"):
        load_records(write_csv("", header=""))


def test_missing_column(write_csv) -> None:
    """Відсутній обов'язковий стовпець називається в повідомленні."""
    path = write_csv("А,мазь,1,1\n", header="name,form,price,days_left\n")

    with pytest.raises(DataError, match="відсутні стовпці: prescription"):
        load_records(path)


def test_bad_number_reports_line_field_and_cause(write_csv) -> None:
    """Хибне число: номер рядка, назва поля й першопричина ValueError."""
    path = write_csv("А,мазь,1,1,false\nБ,мазь,дорого,1,false\n")

    with pytest.raises(DataError, match="рядок 3, поле «price»: очікується число") as caught:
        load_records(path)
    assert isinstance(caught.value.__cause__, ValueError)


def test_fractional_days_are_rejected(write_csv) -> None:
    """days_left — ціле число."""
    with pytest.raises(DataError, match="поле «days_left»: очікується ціле число"):
        load_records(write_csv("А,мазь,1,2.5,false\n"))


@pytest.mark.parametrize("price", ["-1", "nan", "inf"])
def test_negative_or_non_finite_price_is_rejected(write_csv, price: str) -> None:
    """Від'ємні та нескінченні значення заборонені."""
    with pytest.raises(DataError, match="значення має бути невід'ємним"):
        load_records(write_csv(f"А,мазь,{price},1,false\n"))


def test_missing_value_in_row(write_csv) -> None:
    """Рядок коротший за заголовок: DictReader дає None, повідомлення називає поле."""
    with pytest.raises(DataError, match="рядок 2, поле «prescription»: значення відсутнє"):
        load_records(write_csv("А,мазь,1,1\n"))


def test_empty_value_in_row(write_csv) -> None:
    """Порожнє значення поля — помилка."""
    with pytest.raises(DataError, match="поле «name»: порожнє значення"):
        load_records(write_csv(",мазь,1,1,false\n"))


def test_extra_values_in_row(write_csv) -> None:
    """Зайві значення в рядку — помилка."""
    with pytest.raises(DataError, match="зайві значення"):
        load_records(write_csv("А,мазь,1,1,false,зайве\n"))


def test_bad_flag(write_csv) -> None:
    """Невідоме значення логічного поля."""
    with pytest.raises(DataError, match="очікується true або false"):
        load_records(write_csv("А,мазь,1,1,можливо\n"))


def test_missing_file_keeps_os_error_cause(tmp_path: Path) -> None:
    """Файл не існує: DataError з першопричиною OSError."""
    with pytest.raises(DataError, match="не вдалося прочитати файл") as caught:
        load_records(tmp_path / "missing.csv")
    assert isinstance(caught.value.__cause__, FileNotFoundError)


def test_unclosed_quote_is_data_error(write_csv) -> None:
    """Пошкоджений CSV (незакриті лапки в strict-режимі csv) — DataError, а не падіння."""
    path = write_csv('"незакрито,мазь,1,1,false\n')

    with pytest.raises(DataError):
        load_records(path)


def test_iter_records_is_lazy(write_csv) -> None:
    """Генератор читає рядки поступово: перший запис доступний до розбору хибного другого."""
    records = iter_records(write_csv("А,мазь,1,1,false\nБ,мазь,хибно,1,false\n"))

    assert next(records)["name"] == "А"
    with pytest.raises(DataError):
        next(records)


def test_input_file_is_not_modified(sample_path: Path) -> None:
    """Читання не змінює вхідний файл."""
    before = sample_path.read_bytes()

    load_records(sample_path)

    assert sample_path.read_bytes() == before
