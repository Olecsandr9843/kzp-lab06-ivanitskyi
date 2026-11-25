"""Тести звіту та командного рядка."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from kzp_lab06 import cli
from kzp_lab06.analysis import make_summary
from kzp_lab06.reporting import format_report, write_report

EXPECTED_SAMPLE_REPORT = """\
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
"""


def test_write_report_uses_utf8_and_lf(tmp_path: Path) -> None:
    """Запис через with у UTF-8 з \\n незалежно від ОС; каталог створюється."""
    output = tmp_path / "nested" / "report.txt"

    write_report(output, "Готово\nРядок 2\n")

    assert output.read_bytes() == "Готово\nРядок 2\n".encode()


def test_format_report_of_empty_summary() -> None:
    """Звіт для порожнього входу."""
    text = format_report(make_summary([], "price", price="Сума"), "empty.csv")

    assert "Записів: 0\n" in text
    assert "Середня ціна: 0.00 грн\n" in text
    assert "Найближчий термін придатності: немає даних\n" in text
    assert "Форми випуску (0): немає\n" in text


def test_cli_success_writes_expected_report(sample_path: Path, tmp_path: Path, capsys) -> None:
    """Успішний сценарій: код 0, повний очікуваний текст у файлі й у stdout."""
    output = tmp_path / "summary.txt"

    code = cli.main([str(sample_path), str(output)])

    assert code == cli.EXIT_OK
    assert output.read_text(encoding="utf-8") == EXPECTED_SAMPLE_REPORT
    assert capsys.readouterr().out.startswith(EXPECTED_SAMPLE_REPORT)


def test_cli_report_is_deterministic(sample_path: Path, tmp_path: Path) -> None:
    """Два запуски дають однаковий звіт, а порядок рядків у CSV не впливає на результат."""
    lines = sample_path.read_text(encoding="utf-8").splitlines(keepends=True)
    shuffled = tmp_path / "input.csv"
    shuffled.write_text(lines[0] + "".join(reversed(lines[1:])), encoding="utf-8")

    cli.main([str(sample_path), str(tmp_path / "a.txt")])
    cli.main([str(shuffled), str(tmp_path / "b.txt")])

    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == (tmp_path / "b.txt").read_text(
        encoding="utf-8"
    )


def test_cli_data_error_returns_nonzero(write_csv, tmp_path: Path, capsys) -> None:
    """Помилковий сценарій: код 1, повідомлення в stderr, звіт не створено."""
    path = write_csv("А,мазь,дорого,1,false\n")
    output = tmp_path / "out" / "summary.txt"

    code = cli.main([str(path), str(output)])

    assert code == cli.EXIT_DATA_ERROR
    assert "Помилка даних: рядок 2, поле «price»" in capsys.readouterr().err
    assert not output.exists()


def test_cli_missing_input_returns_nonzero(tmp_path: Path, capsys) -> None:
    """Відсутній вхідний файл — код 1."""
    assert cli.main([str(tmp_path / "missing.csv"), str(tmp_path / "r.txt")]) == cli.EXIT_DATA_ERROR
    assert "не вдалося прочитати файл" in capsys.readouterr().err


def test_cli_same_input_and_output_is_rejected(sample_path: Path) -> None:
    """Вхідний CSV не можна перезаписати звітом."""
    assert cli.main([str(sample_path), str(sample_path)]) == cli.EXIT_USAGE


def test_cli_usage_error_and_version(capsys) -> None:
    """argparse: без аргументів — код 2; --version виводить версію."""
    with pytest.raises(SystemExit) as caught:
        cli.main([])
    assert caught.value.code == 2

    with pytest.raises(SystemExit) as caught:
        cli.main(["--version"])
    assert caught.value.code == 0
    assert capsys.readouterr().out.startswith("kzp-lab06 ")


def test_cli_threshold_option(sample_path: Path, tmp_path: Path) -> None:
    """Параметр --threshold змінює відбір."""
    output = tmp_path / "r.txt"

    cli.main([str(sample_path), str(output), "--threshold", "7"])

    assert "Термін придатності ≤ 7 дн.: 2\n" in output.read_text(encoding="utf-8")


def test_module_runs_as_script(sample_path: Path, tmp_path: Path) -> None:
    """``python -m kzp_lab06.cli`` працює як окремий процес і повертає коди завершення."""
    src = Path(__file__).resolve().parent.parent / "src"
    env = {**os.environ, "PYTHONPATH": str(src), "PYTHONIOENCODING": "utf-8"}
    ok = subprocess.run(
        [sys.executable, "-m", "kzp_lab06.cli", str(sample_path), str(tmp_path / "s.txt")],
        capture_output=True,
        env=env,
        check=False,
    )
    bad = subprocess.run(
        [
            sys.executable,
            "-m",
            "kzp_lab06.cli",
            str(tmp_path / "missing.csv"),
            str(tmp_path / "x.txt"),
        ],
        capture_output=True,
        env=env,
        check=False,
    )

    assert ok.returncode == 0, ok.stderr.decode("utf-8", "replace")
    assert bad.returncode == 1
    assert (tmp_path / "s.txt").read_text(encoding="utf-8") == EXPECTED_SAMPLE_REPORT
