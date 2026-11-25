"""ЛР7: властивості, setter-и, спеціальні методи, підтипи, протокол і dataclass."""

import dataclasses

import pytest

from kzp_lab07.models import (
    FreeMedicine,
    Medicine,
    PrescriptionMedicine,
    Scored,
    Summary,
    create_medicine,
)


@pytest.fixture
def paracetamol() -> FreeMedicine:
    """Безрецептурний препарат для тестів."""
    return FreeMedicine("Парацетамол", "Таблетки", 45.5, 365)


# ---------- @property і setter ----------


def test_constructor_normalizes_and_exposes_properties(paracetamol: FreeMedicine) -> None:
    """Властивості повертають перевірені й нормалізовані значення."""
    assert paracetamol.name == "Парацетамол"
    assert paracetamol.form == "таблетки"
    assert paracetamol.price == 45.5
    assert paracetamol.days_left == 365
    assert paracetamol.prescription is False


def test_setter_accepts_valid_zero_and_boundary_values(paracetamol: FreeMedicine) -> None:
    """Коректне, нульове й граничне значення приймаються."""
    paracetamol.price = 39.9
    assert paracetamol.price == 39.9
    paracetamol.price = 0
    assert paracetamol.price == 0.0
    assert isinstance(paracetamol.price, float)
    paracetamol.days_left = 0
    assert paracetamol.days_left == 0


@pytest.mark.parametrize("value", [-0.01, -1, float("nan"), float("inf")])
def test_price_setter_rejects_invalid_values(paracetamol: FreeMedicine, value: float) -> None:
    """Від'ємні та нескінченні значення відхиляються, старе значення не змінюється."""
    with pytest.raises(ValueError, match="поле «price»"):
        paracetamol.price = value
    assert paracetamol.price == 45.5


@pytest.mark.parametrize("value", ["45.5", None, True])
def test_price_setter_rejects_wrong_types(paracetamol: FreeMedicine, value: object) -> None:
    """Рядок, None і bool (підклас int) — не число."""
    with pytest.raises(TypeError, match="поле «price»"):
        paracetamol.price = value  # type: ignore[assignment]


@pytest.mark.parametrize(
    ("value", "error"), [(-1, ValueError), (2.5, TypeError), (False, TypeError)]
)
def test_days_left_setter_validation(paracetamol: FreeMedicine, value: object, error: type) -> None:
    """days_left — ціле ≥ 0."""
    with pytest.raises(error, match="поле «days_left»"):
        paracetamol.days_left = value  # type: ignore[assignment]


def test_name_and_form_are_read_only(paracetamol: FreeMedicine) -> None:
    """Властивості без setter-а не можна змінити."""
    with pytest.raises(AttributeError):
        paracetamol.name = "Інша"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        paracetamol.form = "сироп"  # type: ignore[misc]


@pytest.mark.parametrize(("name", "form"), [("  ", "мазь"), ("А", ""), (None, "мазь")])
def test_constructor_rejects_bad_text(name: object, form: object) -> None:
    """Порожня назва чи форма — ValueError, не текст — TypeError."""
    with pytest.raises((ValueError, TypeError)):
        FreeMedicine(name, form, 1.0, 1)  # type: ignore[arg-type]


def test_base_class_is_abstract() -> None:
    """«Препарат узагалі» створити не можна."""
    with pytest.raises(TypeError):
        Medicine("А", "мазь", 1.0, 1)  # type: ignore[abstract]


# ---------- спеціальні методи ----------


def test_str_and_repr(paracetamol: FreeMedicine) -> None:
    """__str__ — для звіту, __repr__ — для розробника."""
    assert str(paracetamol) == "Парацетамол (таблетки)"
    assert (
        repr(paracetamol)
        == "FreeMedicine(name='Парацетамол', form='таблетки', price=45.5, days_left=365)"
    )


def test_equality_and_hash(paracetamol: FreeMedicine) -> None:
    """Рівні: той самий підтип, назва й форма; ціна й термін не впливають."""
    other_batch = FreeMedicine("Парацетамол", "таблетки", 39.9, 7)

    assert paracetamol == other_batch
    assert hash(paracetamol) == hash(other_batch)
    assert paracetamol != FreeMedicine("Парацетамол", "сироп", 45.5, 365)
    assert paracetamol != PrescriptionMedicine("Парацетамол", "таблетки", 45.5, 365)


def test_eq_returns_not_implemented_for_foreign_type(paracetamol: FreeMedicine) -> None:
    """Для чужого типу __eq__ повертає NotImplemented, а оператор == — False."""
    assert paracetamol.__eq__("Парацетамол") is NotImplemented
    assert paracetamol != "Парацетамол"


def test_objects_work_in_set_and_dict(paracetamol: FreeMedicine) -> None:
    """Узгоджені __eq__ і __hash__: дублікати зливаються в set і dict."""
    duplicate = FreeMedicine("Парацетамол", "таблетки", 1.0, 1)

    assert len({paracetamol, duplicate}) == 1
    assert {paracetamol: "перша"}[duplicate] == "перша"


def test_sort_key_orders_by_expiry_then_name() -> None:
    """sorted(..., key=...) замість __lt__."""
    items = [
        FreeMedicine("Назол", "спрей", 60, 14),
        PrescriptionMedicine("Мелоксикам", "розчин", 155, 0),
        FreeMedicine("Левомеколь", "мазь", 89.75, 14),
    ]

    assert [item.name for item in sorted(items, key=lambda item: item.sort_key)] == [
        "Мелоксикам",
        "Левомеколь",
        "Назол",
    ]


# ---------- підтипи та протокол ----------


def test_subtypes_score_same_data_differently() -> None:
    """Однакові дані — різні формули."""
    prescription = PrescriptionMedicine("Ліки", "таблетки", 100.0, 200)
    free = FreeMedicine("Ліки", "таблетки", 100.0, 200)

    assert prescription.availability_score() == 50  # 60 − 10
    assert free.availability_score() == 90  # 100 − 10


@pytest.mark.parametrize(
    ("medicine", "score"),
    [
        (PrescriptionMedicine("Дорогий", "ампули", 5000, 100), 10),  # нижня межа
        (PrescriptionMedicine("Сьогодні", "таблетки", 1, 0), 0),
        (FreeMedicine("Межа", "сироп", 45.5, 29), 76),  # короткий термін: −20
        (FreeMedicine("Межа", "сироп", 45.5, 30), 96),
        (FreeMedicine("Дорогий", "мазь", 10_000, 365), 50),  # штраф не більше 50
        (FreeMedicine("Сьогодні", "спрей", 1, 0), 0),
    ],
)
def test_subtype_formulas_boundaries(medicine: Medicine, score: int) -> None:
    """Межові випадки кожної формули."""
    assert medicine.availability_score() == score


def test_both_subtypes_satisfy_protocol() -> None:
    """Обидва підтипи відповідають протоколу Scored (перевірка структури, а не спадкування)."""
    assert isinstance(PrescriptionMedicine("А", "мазь", 1, 1), Scored)
    assert isinstance(FreeMedicine("А", "мазь", 1, 1), Scored)


def test_duck_typed_object_satisfies_protocol() -> None:
    """Сторонній клас без спадкування теж підходить — це і є качина типізація."""

    class Voucher:
        name = "Сертифікат"
        days_left = 10

        def availability_score(self) -> int:
            return 100

    assert isinstance(Voucher(), Scored)


def test_factory_picks_subtype_without_if() -> None:
    """Фабрика вибирає клас за словником SUBTYPES."""
    assert type(create_medicine("А", "мазь", 1, 1, True)) is PrescriptionMedicine
    assert type(create_medicine("А", "мазь", 1, 1, False)) is FreeMedicine


# ---------- dataclass ----------


def make_summary(**changes: object) -> Summary:
    """Підсумок для тестів."""
    values = {
        "count": 1,
        "average_price": 1.0,
        "nearest": None,
        "expiring": (),
        "threshold": 30,
        "forms": ("мазь",),
        "by_form": (("мазь", 1),),
        "prescription_count": 0,
        "total_price": 1.0,
        "average_availability": 100.0,
    }
    values.update(changes)
    return Summary(**values)  # type: ignore[arg-type]


def test_summary_is_frozen() -> None:
    """frozen=True: зміна поля — FrozenInstanceError."""
    summary = make_summary()

    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.count = 2  # type: ignore[misc]


def test_summary_equality_and_hash() -> None:
    """@dataclass генерує __eq__ за полями; frozen робить об'єкт хешованим."""
    assert make_summary() == make_summary()
    assert make_summary() != make_summary(count=2)
    assert hash(make_summary()) == hash(make_summary())


def test_summary_fields() -> None:
    """Склад полів підсумку."""
    assert [field.name for field in dataclasses.fields(Summary)] == [
        "count",
        "average_price",
        "nearest",
        "expiring",
        "threshold",
        "forms",
        "by_form",
        "prescription_count",
        "total_price",
        "average_availability",
    ]
