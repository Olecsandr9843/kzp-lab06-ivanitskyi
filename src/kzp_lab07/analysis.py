"""Аналіз асортименту через спільний протокол, без перевірок конкретного підтипу."""

from collections import Counter
from collections.abc import Iterable, Sequence

from .models import Medicine, Scored, Summary

#: Поріг «близького» терміну придатності, днів (включно).
EXPIRY_THRESHOLD = 30


def by_expiry(item: Scored) -> tuple[int, str]:
    """Ключ сортування: спершу найближчий термін, потім назва.

    Працює з будь-яким об'єктом протоколу :class:`Scored`; передається у ``sorted``/``min``
    як ``key`` замість реалізації ``__lt__``.
    """
    return (item.days_left, item.name)


def expiring_soon(items: Iterable[Scored], threshold: int = EXPIRY_THRESHOLD) -> list[Scored]:
    """Відбирає об'єкти з терміном ≤ ``threshold`` днів, відсортовані за :func:`by_expiry`."""
    return sorted((item for item in items if item.days_left <= threshold), key=by_expiry)


def average_availability(items: Iterable[Scored]) -> float:
    """Середня оцінка доступності.

    Кожен об'єкт сам рахує свою оцінку (поліморфний виклик ``availability_score()``) —
    функція не знає й не перевіряє, рецептурний це препарат чи ні.
    """
    scores = [item.availability_score() for item in items]
    return sum(scores) / len(scores) if scores else 0.0


def top_by_availability(items: Iterable[Scored], count: int = 3) -> list[Scored]:
    """Перші ``count`` об'єктів за оцінкою доступності (спаданням), при рівності — за назвою."""
    return sorted(items, key=lambda item: (-item.availability_score(), item.name))[:count]


def summarize(medicines: Sequence[Medicine], threshold: int = EXPIRY_THRESHOLD) -> Summary:
    """Будує незмінний підсумок асортименту.

    Args:
        medicines: препарати будь-яких підтипів.
        threshold: поріг для відбору за терміном придатності.

    Returns:
        :class:`~kzp_lab07.models.Summary` з тими самими показниками, що й звіт ЛР6, і
        середньою оцінкою доступності.
    """
    count = len(medicines)
    total_price = sum(medicine.price for medicine in medicines)
    by_form = Counter(medicine.form for medicine in medicines)
    return Summary(
        count=count,
        average_price=total_price / count if count else 0.0,
        nearest=min(medicines, key=by_expiry, default=None),
        expiring=tuple(expiring_soon(medicines, threshold)),
        threshold=threshold,
        forms=tuple(sorted(by_form)),
        by_form=tuple(sorted(by_form.items())),
        prescription_count=sum(1 for medicine in medicines if medicine.prescription),
        total_price=total_price,
        average_availability=average_availability(medicines),
    )
