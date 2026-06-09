from datetime import UTC, datetime, timedelta

from hypothesis import assume, given
from hypothesis import strategies as st

from domain.model import Batch, OrderLine

batch_quantity = st.integers(min_value=1, max_value=10_000)
line_quantity = st.integers(min_value=1, max_value=10_000)
stock_keeping_unit_text = st.text(alphabet=st.characters(whitelist_categories=["Lu"]), min_size=1, max_size=20)
reference_text = st.text(alphabet=st.characters(whitelist_categories=["Lu", "Nd"]), min_size=1, max_size=20)
estimated_time_of_arrival_days = st.one_of(st.none(), st.integers(min_value=0, max_value=365))


def build_batch(reference: str, stock_keeping_unit: str, quantity: int, days_ahead: int | None) -> Batch:
    estimated_time_of_arrival = (
        (datetime.now(tz=UTC).date() + timedelta(days=days_ahead)) if days_ahead is not None else None
    )
    return Batch(reference, stock_keeping_unit, quantity, estimated_time_of_arrival)


def test_allocating_to_a_batch_reduces_the_available_quantity() -> None:
    batch = Batch("batch-001", "SMALL-TABLE", quantity=20, estimated_time_of_arrival=datetime.now(tz=UTC).date())
    line = OrderLine("order-reference", "SMALL-TABLE", 2)

    batch.allocate(line)

    assert batch.available_quantity == 18


def make_batch_and_line(stock_keeping_unit: str, batch_quantity: int, line_quantity: int) -> tuple[Batch, OrderLine]:
    return (
        Batch("batch-001", stock_keeping_unit, batch_quantity, estimated_time_of_arrival=datetime.now(tz=UTC).date()),
        OrderLine("order-123", stock_keeping_unit, line_quantity),
    )


def test_can_allocate_if_available_greater_than_required() -> None:
    large_batch, small_line = make_batch_and_line("ELEGANT-LAMP", 20, 2)
    assert large_batch.can_allocate(small_line)


def test_cannot_allocate_if_available_smaller_than_required() -> None:
    small_batch, large_line = make_batch_and_line("ELEGANT-LAMP", 2, 20)
    assert small_batch.can_allocate(large_line) is False


def test_can_allocate_if_available_equal_to_required() -> None:
    batch, line = make_batch_and_line("ELEGANT-LAMP", 2, 2)
    assert batch.can_allocate(line)


def test_cannot_allocate_if_stock_keeping_units_do_not_match() -> None:
    batch = Batch("batch-001", "UNCOMFORTABLE-CHAIR", 100, estimated_time_of_arrival=None)
    different_stock_keeping_unit_line = OrderLine("order-123", "EXPENSIVE-TOASTER", 10)
    assert batch.can_allocate(different_stock_keeping_unit_line) is False


def test_allocation_is_idempotent() -> None:
    batch, line = make_batch_and_line("ANGULAR-DESK", 20, 2)
    batch.allocate(line)
    batch.allocate(line)
    assert batch.available_quantity == 18


@given(
    stock_keeping_unit=stock_keeping_unit_text,
    reference=reference_text,
    batch_quantity=batch_quantity,
    line_quantity=line_quantity,
    days=estimated_time_of_arrival_days,
)
def test_allocating_reduces_available_quantity(
    stock_keeping_unit: str, reference: str, batch_quantity: int, line_quantity: int, days: int | None
) -> None:
    assume(batch_quantity >= line_quantity)
    batch = build_batch(reference, stock_keeping_unit, batch_quantity, days)
    line = OrderLine("order-1", stock_keeping_unit, line_quantity)

    batch.allocate(line)

    assert batch.available_quantity == batch_quantity - line_quantity


@given(
    stock_keeping_unit=stock_keeping_unit_text,
    reference=reference_text,
    batch_quantity=batch_quantity,
    line_quantity=line_quantity,
    days=estimated_time_of_arrival_days,
)
def test_can_allocate_iff_sufficient_quantity(
    stock_keeping_unit: str, reference: str, batch_quantity: int, line_quantity: int, days: int | None
) -> None:
    batch = build_batch(reference, stock_keeping_unit, batch_quantity, days)
    line = OrderLine("order-1", stock_keeping_unit, line_quantity)

    result = batch.can_allocate(line)

    assert result == (batch_quantity >= line_quantity)


@given(
    stock_keeping_unit=stock_keeping_unit_text,
    reference=reference_text,
    quantity=batch_quantity,
    days=estimated_time_of_arrival_days,
)
def test_allocation_is_idempotent_with_hypothesis(
    stock_keeping_unit: str, reference: str, quantity: int, days: int | None
) -> None:
    batch = build_batch(reference, stock_keeping_unit, quantity, days)
    line = OrderLine("order-1", stock_keeping_unit, 1)

    batch.allocate(line)
    batch.allocate(line)

    assert batch.available_quantity == quantity - 1


@given(
    stock_keeping_unit=stock_keeping_unit_text,
    other_stock_keeping_unit=stock_keeping_unit_text,
    reference=reference_text,
    quantity=batch_quantity,
    line_quantity=line_quantity,
    days=estimated_time_of_arrival_days,
)
def test_cannot_allocate_if_stock_keeping_units_differ(
    stock_keeping_unit: str,
    other_stock_keeping_unit: str,
    reference: str,
    quantity: int,
    line_quantity: int,
    days: int | None,
) -> None:
    assume(stock_keeping_unit != other_stock_keeping_unit)
    batch = build_batch(reference, stock_keeping_unit, quantity, days)
    line = OrderLine("order-1", other_stock_keeping_unit, line_quantity)

    assert batch.can_allocate(line) is False


@given(
    stock_keeping_unit=stock_keeping_unit_text,
    reference=reference_text,
    quantity=batch_quantity,
    days=estimated_time_of_arrival_days,
)
def test_available_quantity_never_exceeds_purchased(
    stock_keeping_unit: str, reference: str, quantity: int, days: int | None
) -> None:
    batch = build_batch(reference, stock_keeping_unit, quantity, days)
    assert batch.available_quantity <= batch._purchased_quantity


@given(
    stock_keeping_unit=stock_keeping_unit_text,
    reference=reference_text,
    quantity=batch_quantity,
    days_a=st.integers(min_value=1, max_value=100),
    days_b=st.integers(min_value=101, max_value=200),
)
def test_earlier_estimated_time_of_arrival_batch_is_less_than_later(
    stock_keeping_unit: str, reference: str, quantity: int, days_a: int, days_b: int
) -> None:
    today = datetime.now(tz=UTC).date()
    earlier = Batch(reference + "A", stock_keeping_unit, quantity, today + timedelta(days=days_a))
    later = Batch(reference + "B", stock_keeping_unit, quantity, today + timedelta(days=days_b))

    assert earlier < later


@given(stock_keeping_unit=stock_keeping_unit_text, reference=reference_text, quantity=batch_quantity)
def test_in_stock_batch_is_never_greater_than_shipment(stock_keeping_unit: str, reference: str, quantity: int) -> None:
    in_stock = Batch(reference + "S", stock_keeping_unit, quantity, estimated_time_of_arrival=None)
    shipment = Batch(
        reference + "P", stock_keeping_unit, quantity, estimated_time_of_arrival=datetime.now(tz=UTC).date()
    )

    assert not (in_stock > shipment)
