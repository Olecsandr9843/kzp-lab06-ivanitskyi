"""Порівняння пам'яті: повне завантаження проти потокової обробки (завдання із зірочкою).

Запуск з кореня проєкту:  python tools/memory_benchmark.py [кількість_рядків]

Скрипт генерує великий CSV (tools/big.csv, не потрапляє в git), будує підсумок двома
способами, перевіряє, що результати однакові, і виводить пікове використання пам'яті за
tracemalloc та час.
"""

import csv
import itertools
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kzp_lab06.analysis import make_summary, summarize_stream  # noqa: E402
from kzp_lab06.loader import iter_records, load_records  # noqa: E402

FORMS = ("таблетки", "капсули", "сироп", "мазь", "розчин", "спрей")


def generate(path: Path, rows: int) -> None:
    """Записує ``rows`` синтетичних записів; itertools.cycle/islice дають повторюваний набір."""
    forms = itertools.cycle(FORMS)
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(["name", "form", "price", "days_left", "prescription"])
        for number, form in zip(itertools.islice(itertools.count(1), rows), forms, strict=False):
            writer.writerow(
                [
                    f"Препарат {number}",
                    form,
                    f"{number % 500 + 0.5:.2f}",
                    number % 400,
                    number % 3 == 0,
                ]
            )


def measure(label: str, action):
    """Виконує action і повертає (результат, пік пам'яті МБ, секунди)."""
    tracemalloc.start()
    started = time.perf_counter()
    result = action()
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"{label:<28} пік пам'яті {peak / 1_048_576:8.1f} МБ, час {elapsed:6.2f} с")
    return result


def main() -> None:
    """Генерує дані, вимірює обидва підходи й порівнює результати."""
    rows = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
    path = Path(__file__).resolve().parent / "big.csv"
    generate(path, rows)
    print(
        f"Файл: {path.name}, рядків даних: {rows}, розмір {path.stat().st_size / 1_048_576:.1f} МБ"
    )

    full = measure("load_records + make_summary", lambda: make_summary(load_records(path), "price"))
    stream = measure("iter_records + summarize", lambda: summarize_stream(iter_records(path)))

    same = all(
        full[key] == stream[key]
        for key in ("count", "nearest", "by_form", "forms", "prescription_count")
    )
    same = same and abs(full["average_price"] - stream["average_price"]) < 1e-9
    same = same and len(full["expiring"]) == len(stream["expiring"])
    print("Результати однакові:", same)


if __name__ == "__main__":
    main()
