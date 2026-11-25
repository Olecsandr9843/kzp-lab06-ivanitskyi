"""Тести функцій аналізу."""

from pathlib import Path

import pytest

from kzp_lab06.analysis import (
    average_price,
    count_by_form,
    expiring_soon,
    make_summary,
    nearest_expiry,
    unique_forms,
)
from kzp_lab06.loader import Medicine, load_records


def medicine(name: str, form: str, price: float, days: int, prescription: bool = False) -> Medicine:
    """Створює запис для тесту."""
    return Medicine(name=name, form=form, price=price, days_left=days, prescription=prescription)


@pytest.fixture
def records(sample_path: Path) -> list[Medicine]:
    """Записи контрольного файла."""
    return load_records(sample_path)


def test_expiring_soon_boundary_and_order(records: list[Medicine]) -> None:
    """Межа 30 входить, 31 — ні; порядок — термін, потім назва."""
    names = [record["name"] for record in expiring_soon(records)]

    assert names == [
        "Мелоксикам",
        "Парацетамол",
        'Мазь "Левомеколь", 40 г',
        "Назол",
        "Інсулін",
        "Цетиризин",
    ]
    assert "Аторвастатин" not in names  # 31 день


def test_expiring_soon_custom_threshold(records: list[Medicine]) -> None:
    """Типовий параметр threshold можна змінити."""
    assert [record["days_left"] for record in expiring_soon(records, threshold=7)] == [0, 7]


def test_count_by_form_with_duplicates_and_sorted_keys(records: list[Medicine]) -> None:
    """Дублікати рахуються; «Таблетки» нормалізовано до «таблетки»; ключі за абеткою."""
    counts = count_by_form(records)

    assert counts == {
        "капсули": 1,
        "мазь": 1,
        "розчин": 2,
        "спрей": 1,
        "суспензія": 1,
        "таблетки": 5,
    }
    assert list(counts) == sorted(counts)


def test_unique_forms_removes_duplicates(records: list[Medicine]) -> None:
    """Множина не містить повторів."""
    assert unique_forms(records) == {"капсули", "мазь", "розчин", "спрей", "суспензія", "таблетки"}


def test_nearest_expiry_and_tie_break() -> None:
    """Найближчий термін; при рівності — перший за назвою."""
    data = [medicine("Б", "мазь", 1, 5), medicine("А", "мазь", 1, 5), medicine("В", "мазь", 1, 9)]

    assert nearest_expiry(data)["name"] == "А"
    assert nearest_expiry([]) is None


def test_average_price(records: list[Medicine]) -> None:
    """Середня ціна та порожній набір."""
    assert average_price(records) == pytest.approx(1590.95 / 11)
    assert average_price([]) == 0.0


def test_make_summary_accepts_args_defaults_and_kwargs(records: list[Medicine]) -> None:
    """*metrics, типове значення threshold і **labels."""
    summary = make_summary(records, "price", "days_left", price="Сума цін")

    assert summary["threshold"] == 30
    assert summary["metrics"] == {"Сума цін": pytest.approx(1590.95), "days_left": 796}
    assert summary["count"] == 11
    assert summary["prescription_count"] == 5


def test_make_summary_without_metrics_and_with_threshold(records: list[Medicine]) -> None:
    """Без позиційних метрик словник metrics порожній; threshold передається іменовано."""
    summary = make_summary(records, threshold=14)

    assert summary["metrics"] == {}
    assert len(summary["expiring"]) == 4


def test_make_summary_of_empty_input() -> None:
    """Порожній вхід не спричиняє ділення на нуль."""
    summary = make_summary([], "price")

    assert summary["count"] == 0
    assert summary["average_price"] == 0.0
    assert summary["nearest"] is None
    assert summary["forms"] == set()
    assert summary["metrics"] == {"price": 0}


def test_analysis_does_not_modify_input(records: list[Medicine]) -> None:
    """Функції аналізу не змінюють вхідний список."""
    snapshot = [dict(record) for record in records]

    make_summary(records, "price")

    assert records == snapshot


def test_summarize_stream_matches_make_summary(sample_path: Path) -> None:
    """Потоковий підсумок (генератор, один прохід) дає той самий результат, що й повний."""
    from kzp_lab06.analysis import summarize_stream
    from kzp_lab06.loader import iter_records

    full = make_summary(load_records(sample_path), "price")
    stream = summarize_stream(iter_records(sample_path))

    assert stream == {**full, "metrics": {"price": pytest.approx(full["metrics"]["price"])}}


def test_summarize_stream_of_empty_iterator() -> None:
    """Порожній ітератор."""
    from kzp_lab06.analysis import summarize_stream

    summary = summarize_stream(iter([]))

    assert summary["count"] == 0
    assert summary["nearest"] is None
    assert summary["average_price"] == 0.0
