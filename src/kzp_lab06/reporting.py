"""Формування й запис текстового звіту."""

from pathlib import Path

from .loader import Medicine


def _describe(record: Medicine) -> str:
    """Короткий опис препарату для рядка звіту."""
    return f"{record['name']} ({record['form']})"


def format_report(summary: dict[str, object], source: str) -> str:
    """Перетворює підсумок на детермінований текст звіту.

    Порядок рядків і формат чисел фіксовані (два знаки після крапки, форми за абеткою,
    відібрані препарати за терміном і назвою), тому той самий вхід завжди дає той самий текст.

    Args:
        summary: результат :func:`kzp_lab06.analysis.make_summary`.
        source: назва вхідного файла для заголовка.

    Returns:
        Текст звіту; рядки розділені ``\\n``, останній рядок теж завершується ``\\n``.
    """
    nearest = summary["nearest"]
    expiring: list[Medicine] = summary["expiring"]  # type: ignore[assignment]
    forms: set[str] = summary["forms"]  # type: ignore[assignment]
    by_form: dict[str, int] = summary["by_form"]  # type: ignore[assignment]
    metrics: dict[str, float] = summary["metrics"]  # type: ignore[assignment]

    lines = [
        "Звіт аптеки (варіант 11)",
        f"Вхідний файл: {source}",
        f"Записів: {summary['count']}",
        f"Середня ціна: {summary['average_price']:.2f} грн",
    ]
    if nearest is None:
        lines.append("Найближчий термін придатності: немає даних")
    else:
        lines.append(
            f"Найближчий термін придатності: {_describe(nearest)} — {nearest['days_left']} дн."  # type: ignore[index]
        )
    lines.append(f"Рецептурних препаратів: {summary['prescription_count']}")
    lines.append(f"Термін придатності ≤ {summary['threshold']} дн.: {len(expiring)}")
    lines.extend(f"  {_describe(record)}: {record['days_left']} дн." for record in expiring)
    lines.append(f"Форми випуску ({len(forms)}): {', '.join(sorted(forms)) or 'немає'}")
    lines.append("Кількість за формою:")
    lines.extend(f"  {form}: {count}" for form, count in by_form.items())
    lines.extend(f"{label}: {value:.2f}" for label, value in metrics.items())
    return "\n".join(lines) + "\n"


def write_report(path: Path, text: str) -> None:
    """Записує звіт у файл UTF-8, створюючи каталог за потреби.

    ``newline="\\n"`` гарантує однакові роздільники рядків на всіх ОС (інакше у Windows
    Python замінив би ``\\n`` на ``\\r\\n``).

    Args:
        path: шлях до файла звіту.
        text: текст звіту.

    Raises:
        OSError: якщо каталог або файл неможливо створити.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as target:
        target.write(text)
