"""Формування звіту та безпечний запис у файл."""

import os
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

from .analysis import top_by_availability
from .models import Medicine, Summary


def format_report(summary: Summary, source: str) -> str:
    """Перетворює підсумок на текст звіту — той самий формат, що й у ЛР6.

    Args:
        summary: незмінний підсумок.
        source: назва вхідного файла для заголовка.

    Returns:
        Текст звіту; рядки розділені ``\\n``, останній теж завершується ``\\n``.
    """
    lines = [
        "Звіт аптеки (варіант 11)",
        f"Вхідний файл: {source}",
        f"Записів: {summary.count}",
        f"Середня ціна: {summary.average_price:.2f} грн",
    ]
    if summary.nearest is None:
        lines.append("Найближчий термін придатності: немає даних")
    else:
        lines.append(
            f"Найближчий термін придатності: {summary.nearest} — {summary.nearest.days_left} дн."
        )
    lines.append(f"Рецептурних препаратів: {summary.prescription_count}")
    lines.append(f"Термін придатності ≤ {summary.threshold} дн.: {len(summary.expiring)}")
    # str(medicine) — це __str__: «Назва (форма)».
    lines.extend(f"  {medicine}: {medicine.days_left} дн." for medicine in summary.expiring)
    lines.append(f"Форми випуску ({len(summary.forms)}): {', '.join(summary.forms) or 'немає'}")
    lines.append("Кількість за формою:")
    lines.extend(f"  {form}: {count}" for form, count in summary.by_form)
    lines.append(f"Сумарна вартість асортименту: {summary.total_price:.2f}")
    return "\n".join(lines) + "\n"


def format_details(medicines: Sequence[Medicine], summary: Summary, top: int = 3) -> str:
    """Додатковий розділ (``--details``): оцінки доступності, обчислені поліморфно.

    Args:
        medicines: препарати.
        summary: підсумок (для середньої оцінки).
        top: скільки препаратів показати в рейтингу.

    Returns:
        Текст розділу, кожен рядок завершується ``\\n``.
    """
    lines = ["Доступність (0–100):"]
    lines.extend(
        f"  {medicine}, {medicine.LABEL}: {medicine.availability_score()}"
        for medicine in sorted(medicines, key=lambda item: item.sort_key)
    )
    lines.append(f"Середня оцінка доступності: {summary.average_availability:.2f}")
    leaders = top_by_availability(medicines, top)
    lines.append(f"Найдоступніші: {', '.join(str(medicine) for medicine in leaders) or 'немає'}")
    return "\n".join(lines) + "\n"


@contextmanager
def atomic_writer(path: Path) -> Iterator[TextIO]:
    """Контекстний менеджер для безпечного запису текстового файла (завдання із зірочкою).

    Текст пишеться в тимчасовий файл у тому самому каталозі. Лише якщо блок ``with``
    завершився без винятку, тимчасовий файл атомарно замінює цільовий (``os.replace``). Якщо
    стався виняток — тимчасовий файл закривається й видаляється, а попередній вміст
    цільового файла (якщо він був) лишається недоторканим. Виняток не поглинається.

    Args:
        path: цільовий файл; каталог створюється за потреби.

    Yields:
        Відкритий текстовий потік (UTF-8, роздільник рядків ``\\n``).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with open(descriptor, "w", encoding="utf-8", newline="\n") as target:
            yield target
        os.replace(temporary, path)
    except BaseException:
        # Файл уже закрито виходом із внутрішнього with; прибираємо незавершений результат.
        Path(temporary).unlink(missing_ok=True)
        raise


def write_report(path: Path, text: str) -> None:
    """Записує звіт у файл UTF-8 через :func:`atomic_writer`.

    Args:
        path: шлях до файла звіту.
        text: текст звіту.

    Raises:
        OSError: якщо каталог або файл неможливо створити.
    """
    with atomic_writer(path) as target:
        target.write(text)
