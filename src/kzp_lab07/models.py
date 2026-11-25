"""Предметна модель: базовий клас препарату, два підтипи, протокол і підсумок.

Модуль не читає файлів і не формує звітів — лише описує об'єкти та їхню поведінку.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

#: Найвища оцінка доступності.
MAX_SCORE = 100
#: Кожні повні 10 грн ціни знижують доступність на 1 бал, але не більше ніж на 50.
PRICE_STEP = 10.0
MAX_PRICE_PENALTY = 50


@runtime_checkable
class Scored(Protocol):
    """Спільний протокол усього, що має назву, термін і оцінку доступності.

    Функції аналізу залежать лише від цього контракту (качина типізація): будь-який об'єкт із
    такими атрибутами підходить, незалежно від класу. ``runtime_checkable`` дозволяє
    перевірити відповідність через ``isinstance`` у тестах.
    """

    @property
    def name(self) -> str:
        """Назва."""
        ...

    @property
    def days_left(self) -> int:
        """Днів до закінчення терміну придатності."""
        ...

    def availability_score(self) -> int:
        """Оцінка доступності від 0 до 100."""
        ...


class Medicine(ABC):
    """Лікарський препарат — базовий клас для всіх категорій.

    Інкапсульований стан зберігається у «приватних» атрибутах з підкресленням, а доступ до
    нього дають властивості (``@property``). ``name`` і ``form`` лише для читання: вони
    визначають рівність і хеш, тому змінюватися не повинні. ``price`` і ``days_left`` мають
    setter із перевіркою, тож некоректне значення неможливо записати ні в конструкторі, ні
    пізніше.

    Клас абстрактний: «препарат узагалі» не створюється, лише підтипи.

    Args:
        name: назва, непорожня.
        form: форма випуску, непорожня; зберігається в нижньому регістрі.
        price: ціна в гривнях, скінченне число ≥ 0.
        days_left: днів до закінчення терміну придатності, ціле ≥ 0.

    Raises:
        TypeError: значення має хибний тип (наприклад, рядок чи ``bool`` замість числа).
        ValueError: значення порожнє, від'ємне чи нескінченне.
    """

    #: Чи потрібен рецепт — задається в підтипі.
    PRESCRIPTION: bool = False
    #: Підпис категорії для звіту — задається в підтипі.
    LABEL: str = ""

    def __init__(self, name: str, form: str, price: float, days_left: int) -> None:
        self._name = _require_text(name, "name")
        self._form = _require_text(form, "form").lower()
        # Присвоєння через властивості запускає setter-перевірки.
        self.price = price
        self.days_left = days_left

    # ---------- властивості ----------

    @property
    def name(self) -> str:
        """Назва препарату (лише читання)."""
        return self._name

    @property
    def form(self) -> str:
        """Форма випуску в нижньому регістрі (лише читання)."""
        return self._form

    @property
    def price(self) -> float:
        """Ціна в гривнях."""
        return self._price

    @price.setter
    def price(self, value: float) -> None:
        # bool — підклас int у Python, тож відкидаємо його явно.
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError(f"поле «price»: очікується число, отримано {value!r}")
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"поле «price»: значення має бути невід'ємним, отримано {value!r}")
        # Пишемо у внутрішній атрибут: self.price = value тут викликав би setter знову без кінця.
        self._price = float(value)

    @property
    def days_left(self) -> int:
        """Днів до закінчення терміну придатності."""
        return self._days_left

    @days_left.setter
    def days_left(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"поле «days_left»: очікується ціле число, отримано {value!r}")
        if value < 0:
            raise ValueError(f"поле «days_left»: значення має бути невід'ємним, отримано {value!r}")
        self._days_left = value

    @property
    def prescription(self) -> bool:
        """Чи потрібен рецепт (визначається підтипом)."""
        return self.PRESCRIPTION

    @property
    def sort_key(self) -> tuple[int, str]:
        """Ключ упорядкування: спершу найближчий термін, потім назва."""
        return (self._days_left, self._name)

    # ---------- поведінка ----------

    @abstractmethod
    def availability_score(self) -> int:
        """Оцінює доступність для покупця від 0 до 100 — кожен підтип по-своєму."""

    def price_penalty(self) -> int:
        """Спільна частина формули: 1 бал за кожні повні 10 грн, не більше 50."""
        return min(MAX_PRICE_PENALTY, math.floor(self._price / PRICE_STEP))

    # ---------- спеціальні методи ----------

    def __str__(self) -> str:
        """Подання для людини, як у звіті: ``Назол (спрей)``."""
        return f"{self._name} ({self._form})"

    def __repr__(self) -> str:
        """Подання для розробника, з якого можна відтворити об'єкт."""
        return (
            f"{type(self).__name__}(name={self._name!r}, form={self._form!r}, "
            f"price={self._price!r}, days_left={self._days_left!r})"
        )

    def __eq__(self, other: object) -> bool:
        """Рівні препарати: той самий підтип, назва й форма (ціна й термін — властивості партії).

        Для об'єкта іншого типу повертає ``NotImplemented``: Python тоді спробує порівняння з
        іншого боку, а якщо й воно не визначене — поверне ``False``.
        """
        if not isinstance(other, Medicine):
            return NotImplemented
        return type(self) is type(other) and (self._name, self._form) == (other._name, other._form)

    def __hash__(self) -> int:
        """Хеш з тих самих незмінних полів, що й рівність, — об'єкт безпечний як ключ dict."""
        return hash((type(self), self._name, self._form))


class PrescriptionMedicine(Medicine):
    """Рецептурний препарат: рецепт — бар'єр, тому оцінка не вища за 60.

    Формула: ``max(10, 60 − штраф за ціну)``; якщо термін спливає сьогодні — 0.
    """

    PRESCRIPTION = True
    LABEL = "за рецептом"
    BASE_SCORE = 60
    MIN_SCORE = 10

    def availability_score(self) -> int:
        """Оцінка рецептурного препарату."""
        if self.days_left == 0:
            return 0
        return max(self.MIN_SCORE, self.BASE_SCORE - self.price_penalty())


class FreeMedicine(Medicine):
    """Безрецептурний препарат: вільний продаж.

    Формула: ``100 − штраф за ціну``, ще ``− 20``, якщо до кінця терміну менше 30 днів;
    якщо термін спливає сьогодні — 0.
    """

    PRESCRIPTION = False
    LABEL = "без рецепта"
    SHORT_EXPIRY_DAYS = 30
    SHORT_EXPIRY_PENALTY = 20

    def availability_score(self) -> int:
        """Оцінка безрецептурного препарату."""
        if self.days_left == 0:
            return 0
        score = MAX_SCORE - self.price_penalty()
        if self.days_left < self.SHORT_EXPIRY_DAYS:
            score -= self.SHORT_EXPIRY_PENALTY
        return score


#: Відповідність «ознака рецепта → клас»; словник замість if/else.
SUBTYPES: dict[bool, type[Medicine]] = {True: PrescriptionMedicine, False: FreeMedicine}


def create_medicine(
    name: str, form: str, price: float, days_left: int, prescription: bool
) -> Medicine:
    """Створює препарат потрібного підтипу за ознакою рецепта.

    Args:
        name: назва.
        form: форма випуску.
        price: ціна.
        days_left: днів до закінчення терміну.
        prescription: ``True`` — :class:`PrescriptionMedicine`, ``False`` — :class:`FreeMedicine`.

    Returns:
        Об'єкт підтипу :class:`Medicine`.
    """
    return SUBTYPES[prescription](name, form, price, days_left)


@dataclass(frozen=True)
class Summary:
    """Незмінний підсумок аналізу асортименту.

    ``frozen=True`` забороняє змінювати поля після створення (``FrozenInstanceError``) і
    робить об'єкт хешованим; колекції подано кортежами, щоб незмінним був і вміст.
    ``@dataclass`` сам генерує ``__init__``, ``__repr__`` і ``__eq__`` за полями.
    """

    count: int
    average_price: float
    nearest: Medicine | None
    #: Препарати з близьким терміном (підсумок варіанта), відсортовані за терміном і назвою.
    expiring: tuple[Medicine, ...]
    threshold: int
    forms: tuple[str, ...]
    by_form: tuple[tuple[str, int], ...]
    prescription_count: int
    total_price: float
    average_availability: float


def _require_text(value: object, field: str) -> str:
    """Перевіряє обов'язковий текст і нормалізує пробіли."""
    if not isinstance(value, str):
        raise TypeError(f"поле «{field}»: очікується текст, отримано {value!r}")
    text = " ".join(value.split())
    if not text:
        raise ValueError(f"поле «{field}»: порожнє значення")
    return text
