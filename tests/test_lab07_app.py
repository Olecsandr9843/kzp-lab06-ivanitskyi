"""ЛР7: loader, analysis, reporting, контекстний менеджер, CLI і сумісність зі звітом ЛР6."""

from pathlib import Path

import pytest

from kzp_lab06 import cli as cli6
from kzp_lab07 import cli as cli7
from kzp_lab07.analysis import average_availability, expiring_soon, summarize, top_by_availability
from kzp_lab07.errors import DataError
from kzp_lab07.loader import iter_medicines, load_medicines
from kzp_lab07.models import FreeMedicine, PrescriptionMedicine
from kzp_lab07.reporting import atomic_writer, format_report, write_report

# ---------- loader ----------


def test_loader_creates_subtype_objects(sample_path: Path) -> None:
    """CSV → об'єкти потрібних підтипів."""
    medicines = load_medicines(sample_path)

    assert len(medicines) == 11
    assert type(medicines[0]) is FreeMedicine
    assert type(medicines[1]) is PrescriptionMedicine
    assert medicines[3].form == "таблетки"  # «Таблетки» нормалізовано моделлю


def test_loader_header_only_and_empty_file(write_csv) -> None:
    """Порожній вхід: лише заголовок — [], без заголовка — DataError."""
    assert load_medicines(write_csv("")) == []
    with pytest.raises(DataError, match="немає рядка заголовка"):
        load_medicines(write_csv("", header=""))


def test_loader_format_error_has_line_field_and_cause(write_csv) -> None:
    """Хибний формат числа: номер рядка, поле, першопричина ValueError."""
    with pytest.raises(DataError, match="рядок 3, поле «price»: очікується число") as caught:
        load_medicines(write_csv("А,мазь,1,1,false\nБ,мазь,дорого,1,false\n"))
    assert isinstance(caught.value.__cause__, ValueError)


def test_loader_invariant_error_comes_from_setter(write_csv) -> None:
    """Від'ємне значення відхиляє setter моделі; loader додає номер рядка."""
    with pytest.raises(
        DataError, match="рядок 2, поле «days_left»: значення має бути невід'ємним"
    ) as caught:
        load_medicines(write_csv("А,мазь,1,-3,false\n"))
    assert isinstance(caught.value.__cause__, ValueError)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("А,мазь,1,1\n", "поле «prescription»: значення відсутнє"),
        (",мазь,1,1,false\n", "поле «name»: порожнє значення"),
        ("А,мазь,1,1,false,зайве\n", "зайві значення"),
        ("А,мазь,1,1,можливо\n", "очікується true або false"),
        ("А,мазь,1,2.5,false\n", "очікується ціле число"),
    ],
)
def test_loader_rejects_damaged_rows(write_csv, body: str, message: str) -> None:
    """Пошкоджені рядки."""
    with pytest.raises(DataError, match=message):
        load_medicines(write_csv(body))


def test_loader_missing_column_and_file(write_csv, tmp_path: Path) -> None:
    """Відсутній стовпець і відсутній файл."""
    with pytest.raises(DataError, match="відсутні стовпці: prescription"):
        load_medicines(write_csv("А,мазь,1,1\n", header="name,form,price,days_left\n"))
    with pytest.raises(DataError) as caught:
        load_medicines(tmp_path / "missing.csv")
    assert isinstance(caught.value.__cause__, FileNotFoundError)


def test_iter_medicines_is_lazy(write_csv) -> None:
    """Генератор: перший об'єкт доступний до розбору хибного другого рядка."""
    medicines = iter_medicines(write_csv("А,мазь,1,1,false\nБ,мазь,х,1,false\n"))

    assert next(medicines).name == "А"
    with pytest.raises(DataError):
        next(medicines)


# ---------- analysis через протокол ----------


def test_analysis_works_on_mixed_subtypes(sample_path: Path) -> None:
    """Спільні функції обробляють обидва підтипи одним кодом."""
    medicines = load_medicines(sample_path)

    assert [item.days_left for item in expiring_soon(medicines)] == [0, 7, 14, 14, 20, 30]
    assert average_availability(medicines) == pytest.approx(655 / 11)
    assert [str(item) for item in top_by_availability(medicines, 2)] == [
        "Парацетамол (таблетки)",
        "Цетиризин (таблетки)",
    ]


def test_summarize_duplicates_and_values(sample_path: Path) -> None:
    """Дублікати назви рахуються як окремі записи; форми — множина без повторів."""
    summary = summarize(load_medicines(sample_path))

    assert summary.count == 11
    assert summary.prescription_count == 5
    assert summary.forms == ("капсули", "мазь", "розчин", "спрей", "суспензія", "таблетки")
    assert dict(summary.by_form)["таблетки"] == 5
    assert summary.nearest is not None and summary.nearest.name == "Мелоксикам"
    assert summary.total_price == pytest.approx(1590.95)


def test_summarize_empty_input() -> None:
    """Порожній вхід: нулі й None без винятків."""
    summary = summarize([])

    assert summary.count == 0
    assert summary.average_price == 0.0
    assert summary.nearest is None
    assert summary.expiring == ()
    assert summary.average_availability == 0.0


# ---------- сумісність зі звітом ЛР6 ----------


@pytest.mark.parametrize("body", ["", "reversed"])
def test_report_is_identical_to_lab06(
    sample_path: Path, tmp_path: Path, write_csv, body: str
) -> None:
    """Той самий CSV — той самий звіт у ЛР6 (словники) і ЛР7 (об'єкти)."""
    if body == "reversed":
        lines = sample_path.read_text(encoding="utf-8").splitlines(keepends=True)
        source = write_csv("".join(reversed(lines[1:])))
    else:
        source = sample_path
    report6 = tmp_path / "lab06.txt"
    report7 = tmp_path / "lab07.txt"

    assert cli6.main([str(source), str(report6)]) == 0
    assert cli7.main([str(source), str(report7)]) == 0
    assert report7.read_text(encoding="utf-8") == report6.read_text(encoding="utf-8")


def test_report_of_empty_input_is_identical_to_lab06(write_csv, tmp_path: Path) -> None:
    """Порожній вхід теж дає однаковий звіт."""
    source = write_csv("")

    cli6.main([str(source), str(tmp_path / "a.txt")])
    cli7.main([str(source), str(tmp_path / "b.txt")])

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == (tmp_path / "b.txt").read_text(
        encoding="utf-8"
    )


def test_format_report_starts_with_header(sample_path: Path) -> None:
    """Заголовок звіту."""
    assert format_report(summarize(load_medicines(sample_path)), "input.csv").startswith(
        "Звіт аптеки (варіант 11)\n"
    )


# ---------- контекстний менеджер (зірочка) ----------


def test_atomic_writer_writes_utf8_lf(tmp_path: Path) -> None:
    """Успішний запис: UTF-8 і \\n, каталог створюється, тимчасових файлів не лишається."""
    target = tmp_path / "nested" / "report.txt"

    write_report(target, "Рядок 1\nРядок 2\n")

    assert target.read_bytes() == "Рядок 1\nРядок 2\n".encode()
    assert [path.name for path in target.parent.iterdir()] == ["report.txt"]


def test_atomic_writer_closes_and_rolls_back_on_exception(tmp_path: Path) -> None:
    """Виняток у блоці with: файл закрито, тимчасовий видалено, старий вміст збережено."""
    target = tmp_path / "report.txt"
    target.write_text("старий звіт\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="збій"), atomic_writer(target) as stream:
        stream.write("напівготовий")
        opened = stream
        raise RuntimeError("збій під час запису")

    assert opened.closed
    assert target.read_text(encoding="utf-8") == "старий звіт\n"
    assert [path.name for path in tmp_path.iterdir()] == ["report.txt"]


def test_atomic_writer_does_not_create_file_on_exception(tmp_path: Path) -> None:
    """Якщо цільового файла не було, після винятку його й не з'являється."""
    target = tmp_path / "new.txt"

    with pytest.raises(ValueError), atomic_writer(target):
        raise ValueError("стоп")

    assert not target.exists()


# ---------- CLI ----------


def test_cli_success_and_details(sample_path: Path, tmp_path: Path, capsys) -> None:
    """Код 0; --details додає розділ з оцінками, обчисленими поліморфно."""
    output = tmp_path / "summary.txt"

    assert cli7.main([str(sample_path), str(output), "--details"]) == cli7.EXIT_OK

    text = output.read_text(encoding="utf-8")
    assert "Доступність (0–100):\n  Мелоксикам (розчин), за рецептом: 0\n" in text
    assert "Середня оцінка доступності: 59.55\n" in text
    assert capsys.readouterr().out.startswith("Звіт аптеки (варіант 11)\n")


def test_cli_data_error(write_csv, tmp_path: Path, capsys) -> None:
    """Код 1, повідомлення в stderr, звіт не створено."""
    output = tmp_path / "summary.txt"

    assert cli7.main([str(write_csv("А,мазь,-1,1,false\n")), str(output)]) == cli7.EXIT_DATA_ERROR
    assert "Помилка даних: рядок 2, поле «price»" in capsys.readouterr().err
    assert not output.exists()


def test_cli_usage_errors(sample_path: Path, capsys) -> None:
    """Код 2: без аргументів (argparse) і вхід = вихід; --version."""
    with pytest.raises(SystemExit) as caught:
        cli7.main([])
    assert caught.value.code == 2
    assert cli7.main([str(sample_path), str(sample_path)]) == cli7.EXIT_USAGE
    with pytest.raises(SystemExit):
        cli7.main(["--version"])
    assert capsys.readouterr().out.startswith("kzp-lab07 ")
