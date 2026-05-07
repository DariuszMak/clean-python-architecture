from datetime import UTC, datetime, timedelta

from hypothesis import assume, given
from hypothesis import strategies as st

from allocation.domain.model import Batch, OrderLine


def test_allocating_to_a_batch_reduces_the_available_quantity() -> None:
    batch = Batch("batch-001", "SMALL-TABLE", qty=20, eta=datetime.now(tz=UTC).date())
    line = OrderLine("order-ref", "SMALL-TABLE", 2)

    batch.allocate(line)

    assert batch.available_quantity == 18


def make_batch_and_line(sku: str, batch_qty: int, line_qty: int) -> tuple[Batch, OrderLine]:
    return (
        Batch("batch-001", sku, batch_qty, eta=datetime.now(tz=UTC).date()),
        OrderLine("order-123", sku, line_qty),
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


def test_cannot_allocate_if_skus_do_not_match() -> None:
    batch = Batch("batch-001", "UNCOMFORTABLE-CHAIR", 100, eta=None)
    different_sku_line = OrderLine("order-123", "EXPENSIVE-TOASTER", 10)
    assert batch.can_allocate(different_sku_line) is False


def test_allocation_is_idempotent() -> None:
    batch, line = make_batch_and_line("ANGULAR-DESK", 20, 2)
    batch.allocate(line)
    batch.allocate(line)
    assert batch.available_quantity == 18


def build_batch(ref: str, sku: str, qty: int, days_ahead: int | None) -> Batch:
    eta = (datetime.now(tz=UTC).date() + timedelta(days=days_ahead)) if days_ahead is not None else None
    return Batch(ref, sku, qty, eta)


batch_qty = st.integers(min_value=1, max_value=10_000)
line_qty = st.integers(min_value=1, max_value=10_000)
sku_text = st.text(alphabet=st.characters(whitelist_categories=("Lu",)), min_size=1, max_size=20)
ref_text = st.text(alphabet=st.characters(whitelist_categories=("Lu", "Nd")), min_size=1, max_size=20)
eta_days = st.one_of(st.none(), st.integers(min_value=0, max_value=365))


@given(sku=sku_text, ref=ref_text, batch_qty=batch_qty, line_qty=line_qty, days=eta_days)
def test_allocating_reduces_available_quantity(
    sku: str, ref: str, batch_qty: int, line_qty: int, days: int | None
) -> None:
    assume(batch_qty >= line_qty)
    batch = build_batch(ref, sku, batch_qty, days)
    line = OrderLine("order-1", sku, line_qty)

    batch.allocate(line)

    assert batch.available_quantity == batch_qty - line_qty


@given(sku=sku_text, ref=ref_text, batch_qty=batch_qty, line_qty=line_qty, days=eta_days)
def test_can_allocate_iff_sufficient_quantity(
    sku: str, ref: str, batch_qty: int, line_qty: int, days: int | None
) -> None:
    batch = build_batch(ref, sku, batch_qty, days)
    line = OrderLine("order-1", sku, line_qty)

    result = batch.can_allocate(line)

    assert result == (batch_qty >= line_qty)


@given(sku=sku_text, ref=ref_text, qty=batch_qty, days=eta_days)
def test_allocation_is_idempotent_with_hypothesis(sku: str, ref: str, qty: int, days: int | None) -> None:
    batch = build_batch(ref, sku, qty, days)
    line = OrderLine("order-1", sku, 1)

    batch.allocate(line)
    batch.allocate(line)

    assert batch.available_quantity == qty - 1


@given(
    sku=sku_text,
    other_sku=sku_text,
    ref=ref_text,
    qty=batch_qty,
    line_qty=line_qty,
    days=eta_days,
)
def test_cannot_allocate_if_skus_differ(
    sku: str, other_sku: str, ref: str, qty: int, line_qty: int, days: int | None
) -> None:
    assume(sku != other_sku)
    batch = build_batch(ref, sku, qty, days)
    line = OrderLine("order-1", other_sku, line_qty)

    assert batch.can_allocate(line) is False


@given(sku=sku_text, ref=ref_text, qty=batch_qty, days=eta_days)
def test_available_quantity_never_exceeds_purchased(sku: str, ref: str, qty: int, days: int | None) -> None:
    batch = build_batch(ref, sku, qty, days)
    assert batch.available_quantity <= batch._purchased_quantity


@given(
    sku=sku_text,
    ref=ref_text,
    qty=batch_qty,
    days_a=st.integers(min_value=1, max_value=100),
    days_b=st.integers(min_value=101, max_value=200),
)
def test_earlier_eta_batch_is_less_than_later(sku: str, ref: str, qty: int, days_a: int, days_b: int) -> None:
    today = datetime.now(tz=UTC).date()
    earlier = Batch(ref + "A", sku, qty, today + timedelta(days=days_a))
    later = Batch(ref + "B", sku, qty, today + timedelta(days=days_b))

    assert earlier < later


@given(sku=sku_text, ref=ref_text, qty=batch_qty)
def test_in_stock_batch_is_never_greater_than_shipment(sku: str, ref: str, qty: int) -> None:
    in_stock = Batch(ref + "S", sku, qty, eta=None)
    shipment = Batch(ref + "P", sku, qty, eta=datetime.now(tz=UTC).date())

    assert not (in_stock > shipment)
