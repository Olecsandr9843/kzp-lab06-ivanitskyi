"""Командний рядок: ``kzp-lab07 data/input.csv reports/summary.txt [--details]``."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .analysis import EXPIRY_THRESHOLD, summarize
from .errors import DataError
from .loader import load_medicines
from .reporting import format_details, format_report, write_report

EXIT_OK = 0
EXIT_DATA_ERROR = 1
EXIT_USAGE = 2  # так завершується argparse при хибних аргументах


def _use_utf8(stream) -> None:
    """Перемикає потік на UTF-8, бо консоль Windows може мати інше кодування."""
    try:
        stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def build_parser() -> argparse.ArgumentParser:
    """Створює розбирач аргументів."""
    parser = argparse.ArgumentParser(
        prog="kzp-lab07",
        description="Об'єктно-орієнтований звіт аптеки з CSV (варіант 11).",
    )
    parser.add_argument("input_csv", type=Path, help="вхідний CSV у UTF-8")
    parser.add_argument("output_report", type=Path, help="файл звіту")
    parser.add_argument(
        "--threshold",
        type=int,
        default=EXPIRY_THRESHOLD,
        help=f"поріг терміну придатності в днях (типово {EXPIRY_THRESHOLD})",
    )
    parser.add_argument(
        "--details", action="store_true", help="додати оцінки доступності препаратів"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Будує звіт з CSV і записує його у файл.

    Args:
        argv: аргументи без імені програми; ``None`` — взяти з ``sys.argv``.

    Returns:
        0 — успіх, 1 — помилка даних або файла, 2 — хибні аргументи.
    """
    _use_utf8(sys.stdout)
    _use_utf8(sys.stderr)
    args = build_parser().parse_args(argv)
    if args.input_csv.resolve() == args.output_report.resolve():
        print("Помилка: вхідний файл і звіт мають бути різними файлами", file=sys.stderr)
        return EXIT_USAGE
    try:
        medicines = load_medicines(args.input_csv)
        summary = summarize(medicines, args.threshold)
        text = format_report(summary, args.input_csv.name)
        if args.details:
            text += format_details(medicines, summary)
        write_report(args.output_report, text)
    except DataError as error:
        print(f"Помилка даних: {error}", file=sys.stderr)
        return EXIT_DATA_ERROR
    except OSError as error:
        print(f"Помилка запису звіту: {error}", file=sys.stderr)
        return EXIT_DATA_ERROR
    print(text, end="")
    print(f"Звіт збережено у файл: {args.output_report}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
