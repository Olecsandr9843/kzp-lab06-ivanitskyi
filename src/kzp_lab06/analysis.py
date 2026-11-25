"""Аналіз записів: відбір, агрегування за ключем, унікальні значення, підсумок."""

from collections.abc import Iterable

from .loader import Medicine

#: Поріг «короткого» терміну придатності, днів (включно) — відбір варіанта 11.
EXPIRY_THRESHOLD = 30


def expiring_soon(records: Iterable[Medicine], threshold: int = EXPIRY_THRESHOLD) -> list[Medicine]:
    """Відбирає препарати, термін придатності яких спливає не пізніше ніж за ``threshold`` днів.

    Результат відсортовано за терміном, потім за назвою, щоб звіт був однаковим за будь-якого
    порядку рядків у файлі.

    Args:
        records: записи.
        threshold: поріг у днях, включно.

    Returns:
        Новий список; вхідні записи не змінюються.
    """
    # list comprehension: відбір; sorted з ключем-кортежем: основний і другорядний критерій.
    selected = [record for record in records if record["days_left"] <= threshold]
    return sorted(selected, key=lambda record: (record["days_left"], record["name"]))


def count_by_form(records: Iterable[Medicine]) -> dict[str, int]:
    """Рахує кількість препаратів за формою випуску.

    Args:
        records: записи.

    Returns:
        Словник «форма → кількість» з ключами в алфавітному порядку.
    """
    counts: dict[str, int] = {}
    for record in records:
        counts[record["form"]] = counts.get(record["form"], 0) + 1
    # dict comprehension відновлює стабільний (алфавітний) порядок ключів.
    return {form: counts[form] for form in sorted(counts)}


def unique_forms(records: Iterable[Medicine]) -> set[str]:
    """Повертає множину форм випуску без повторів.

    Args:
        records: записи.

    Returns:
        Множина (set comprehension); порядок не визначений — для звіту її сортують.
    """
    return {record["form"] for record in records}


def nearest_expiry(records: Iterable[Medicine]) -> Medicine | None:
    """Знаходить препарат з найближчим терміном придатності (при рівності — перший за назвою).

    Args:
        records: записи.

    Returns:
        Запис або ``None``, якщо записів немає.
    """
    return min(records, key=lambda record: (record["days_left"], record["name"]), default=None)


def average_price(records: Iterable[Medicine]) -> float:
    """Обчислює середню ціну.

    Args:
        records: записи.

    Returns:
        Середнє арифметичне цін або ``0.0`` для порожнього набору.
    """
    prices = [record["price"] for record in records]
    return sum(prices) / len(prices) if prices else 0.0


def make_summary(
    records: list[Medicine],
    *metrics: str,
    threshold: int = EXPIRY_THRESHOLD,
    **labels: str,
) -> dict[str, object]:
    """Формує підсумок для звіту.

    Args:
        records: записи.
        *metrics: назви числових полів (``"price"``, ``"days_left"``), для яких додатково
            порахувати суму; усередині функції це кортеж рядків.
        threshold: поріг для відбору за терміном придатності (типове значення — 30 днів).
        **labels: підписи для метрик у звіті, наприклад ``price="Сумарна вартість"``;
            усередині функції це словник.

    Returns:
        Словник із ключами ``count``, ``average_price``, ``nearest``, ``expiring``,
        ``threshold``, ``forms``, ``by_form``, ``prescription_count`` і ``metrics``
        (словник «підпис → сума»).

    Raises:
        KeyError: якщо метрика не є полем запису.
    """
    return {
        "count": len(records),
        "average_price": average_price(records),
        "nearest": nearest_expiry(records),
        "expiring": expiring_soon(records, threshold),
        "threshold": threshold,
        "forms": unique_forms(records),
        "by_form": count_by_form(records),
        "prescription_count": sum(1 for record in records if record["prescription"]),
        "metrics": {
            labels.get(metric, metric): sum(record[metric] for record in records)
            for metric in metrics
        },
    }


def summarize_stream(
    records: Iterable[Medicine], threshold: int = EXPIRY_THRESHOLD
) -> dict[str, object]:
    """Будує той самий підсумок, що й :func:`make_summary`, за один прохід (завдання із зірочкою).

    Приймає будь-який ітератор (наприклад, генератор :func:`kzp_lab06.loader.iter_records`) і
    не зберігає всі записи: у пам'яті лише лічильники, найближчий запис і відібрані препарати
    з коротким терміном. Тому придатний для файлів, що не вміщаються в пам'ять.

    Args:
        records: записи, які можна пройти лише один раз.
        threshold: поріг для відбору за терміном придатності.

    Returns:
        Словник з тими самими ключами, що й у :func:`make_summary` без метрик, плюс
        ``metrics`` із сумою цін під ключем ``"price"``.
    """
    count = 0
    total_price = 0.0
    prescriptions = 0
    nearest: Medicine | None = None
    by_form: dict[str, int] = {}
    expiring: list[Medicine] = []
    for record in records:
        count += 1
        total_price += record["price"]
        prescriptions += record["prescription"]
        by_form[record["form"]] = by_form.get(record["form"], 0) + 1
        key = (record["days_left"], record["name"])
        if nearest is None or key < (nearest["days_left"], nearest["name"]):
            nearest = record
        if record["days_left"] <= threshold:
            expiring.append(record)
    return {
        "count": count,
        "average_price": total_price / count if count else 0.0,
        "nearest": nearest,
        "expiring": sorted(expiring, key=lambda record: (record["days_left"], record["name"])),
        "threshold": threshold,
        "forms": set(by_form),
        "by_form": {form: by_form[form] for form in sorted(by_form)},
        "prescription_count": prescriptions,
        "metrics": {"price": total_price},
    }
