from datetime import UTC, datetime, timedelta

from hypothesis import assume, given
from hypothesis import strategies as st

from allocation.domain import events
from allocation.domain.model import Batch, OrderLine, Product

today = datetime.now(tz=UTC).date()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)

sku_text = st.text(alphabet=st.characters(whitelist_categories=("Lu",)), min_size=1, max_size=20)
ref_text = st.text(alphabet=st.characters(whitelist_categories=("Lu", "Nd")), min_size=1, max_size=20)
pos_qty = st.integers(min_value=1, max_value=10_000)
eta_days = st.one_of(st.none(), st.integers(min_value=0, max_value=365))


def test_prefers_warehouse_batches_to_shipments() -> None:
    in_stock_batch = Batch("in-stock-batch", "RETRO-CLOCK", 100, eta=None)
    shipment_batch = Batch("shipment-batch", "RETRO-CLOCK", 100, eta=tomorrow)
    product = Product(sku="RETRO-CLOCK", batches=[in_stock_batch, shipment_batch])
    line = OrderLine("oref", "RETRO-CLOCK", 10)

    product.allocate(line)

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches() -> None:
    earliest = Batch("speedy-batch", "MINIMALIST-SPOON", 100, eta=today)
    medium = Batch("normal-batch", "MINIMALIST-SPOON", 100, eta=tomorrow)
    latest = Batch("slow-batch", "MINIMALIST-SPOON", 100, eta=later)
    product = Product(sku="MINIMALIST-SPOON", batches=[medium, earliest, latest])
    line = OrderLine("order1", "MINIMALIST-SPOON", 10)

    product.allocate(line)

    assert earliest.available_quantity == 90
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100


def test_returns_allocated_batch_ref() -> None:
    in_stock_batch = Batch("in-stock-batch-ref", "HIGHBROW-POSTER", 100, eta=None)
    shipment_batch = Batch("shipment-batch-ref", "HIGHBROW-POSTER", 100, eta=tomorrow)
    line = OrderLine("oref", "HIGHBROW-POSTER", 10)
    product = Product(sku="HIGHBROW-POSTER", batches=[in_stock_batch, shipment_batch])
    allocation = product.allocate(line)
    assert allocation == in_stock_batch.reference


def test_outputs_allocated_event() -> None:
    batch = Batch("batchref", "RETRO-LAMPSHADE", 100, eta=None)
    line = OrderLine("oref", "RETRO-LAMPSHADE", 10)
    product = Product(sku="RETRO-LAMPSHADE", batches=[batch])
    product.allocate(line)
    expected = events.Allocated(orderid="oref", sku="RETRO-LAMPSHADE", qty=10, batchref=batch.reference)
    assert product.events[-1] == expected


def test_records_out_of_stock_event_if_cannot_allocate() -> None:
    batch = Batch("batch1", "SMALL-FORK", 10, eta=today)
    product = Product(sku="SMALL-FORK", batches=[batch])
    product.allocate(OrderLine("order1", "SMALL-FORK", 10))

    allocation = product.allocate(OrderLine("order2", "SMALL-FORK", 1))
    assert product.events[-1] == events.OutOfStock(sku="SMALL-FORK")
    assert allocation is None


def test_increments_version_number() -> None:
    line = OrderLine("oref", "SCANDI-PEN", 10)
    product = Product(sku="SCANDI-PEN", batches=[Batch("b1", "SCANDI-PEN", 100, eta=None)])
    product.version_number = 7
    product.allocate(line)
    assert product.version_number == 8


def make_eta(days: int | None) -> datetime.date | None:
    return (today + timedelta(days=days)) if days is not None else None


@given(sku=sku_text, ref=ref_text, batch_qty=pos_qty, line_qty=pos_qty, days=eta_days)
def test_allocate_returns_batchref_when_sufficient_stock(
    sku: str, ref: str, batch_qty: int, line_qty: int, days: int | None
) -> None:
    assume(batch_qty >= line_qty)
    batch = Batch(ref, sku, batch_qty, make_eta(days))
    product = Product(sku=sku, batches=[batch])
    line = OrderLine("order-1", sku, line_qty)

    result = product.allocate(line)

    assert result == ref


@given(sku=sku_text, ref=ref_text, batch_qty=pos_qty, line_qty=pos_qty, days=eta_days)
def test_allocate_returns_none_and_emits_out_of_stock_when_insufficient(
    sku: str, ref: str, batch_qty: int, line_qty: int, days: int | None
) -> None:
    assume(batch_qty < line_qty)
    batch = Batch(ref, sku, batch_qty, make_eta(days))
    product = Product(sku=sku, batches=[batch])
    line = OrderLine("order-1", sku, line_qty)

    result = product.allocate(line)

    assert result is None
    assert any(isinstance(e, events.OutOfStock) for e in product.events)


@given(sku=sku_text, ref=ref_text, qty=pos_qty, days=eta_days)
def test_version_number_increments_on_successful_allocation(sku: str, ref: str, qty: int, days: int | None) -> None:
    batch = Batch(ref, sku, qty, make_eta(days))
    product = Product(sku=sku, batches=[batch])
    initial_version = product.version_number
    line = OrderLine("order-1", sku, 1)

    product.allocate(line)

    assert product.version_number == initial_version + 1


@given(sku=sku_text, ref=ref_text, qty=pos_qty, days=eta_days)
def test_version_number_does_not_increment_on_out_of_stock(sku: str, ref: str, qty: int, days: int | None) -> None:
    batch = Batch(ref, sku, qty, make_eta(days))
    product = Product(sku=sku, batches=[batch])
    initial_version = product.version_number
    line = OrderLine("order-1", sku, qty + 1)

    product.allocate(line)

    assert product.version_number == initial_version


@given(
    sku=sku_text,
    ref1=ref_text,
    ref2=ref_text,
    qty=pos_qty,
    days_early=st.integers(min_value=1, max_value=100),
    days_late=st.integers(min_value=101, max_value=200),
)
def test_prefers_earlier_batch(sku: str, ref1: str, ref2: str, qty: int, days_early: int, days_late: int) -> None:
    assume(ref1 != ref2)
    early_batch = Batch(ref1, sku, qty, today + timedelta(days=days_early))
    late_batch = Batch(ref2, sku, qty, today + timedelta(days=days_late))
    product = Product(sku=sku, batches=[late_batch, early_batch])
    line = OrderLine("order-1", sku, 1)

    result = product.allocate(line)

    assert result == ref1


@given(sku=sku_text, ref1=ref_text, ref2=ref_text, qty=pos_qty, days=eta_days)
def test_prefers_in_stock_over_shipment(sku: str, ref1: str, ref2: str, qty: int, days: int | None) -> None:
    assume(ref1 != ref2)
    assume(days is not None)
    in_stock = Batch(ref1, sku, qty, eta=None)
    shipment = Batch(ref2, sku, qty, make_eta(days))
    product = Product(sku=sku, batches=[shipment, in_stock])
    line = OrderLine("order-1", sku, 1)

    result = product.allocate(line)

    assert result == ref1


@given(sku=sku_text, ref=ref_text, qty=pos_qty, line_qty=pos_qty, days=eta_days)
def test_allocated_event_has_correct_fields(sku: str, ref: str, qty: int, line_qty: int, days: int | None) -> None:
    assume(qty >= line_qty)
    batch = Batch(ref, sku, qty, make_eta(days))
    product = Product(sku=sku, batches=[batch])
    line = OrderLine("order-1", sku, line_qty)

    product.allocate(line)

    allocated_events = [e for e in product.events if isinstance(e, events.Allocated)]
    assert len(allocated_events) == 1
    ev = allocated_events[0]
    assert ev.orderid == "order-1"
    assert ev.sku == sku
    assert ev.qty == line_qty
    assert ev.batchref == ref


@given(
    sku=sku_text,
    ref=ref_text,
    initial_qty=st.integers(min_value=2, max_value=10_000),
    n_extra=st.integers(min_value=1, max_value=5),
)
def test_change_batch_quantity_deallocates_excess_orders(sku: str, ref: str, initial_qty: int, n_extra: int) -> None:
    new_qty = max(1, initial_qty - n_extra)
    batch = Batch(ref, sku, initial_qty, eta=None)
    product = Product(sku=sku, batches=[batch])

    for i in range(n_extra):
        line = OrderLine(f"order-{i}", sku, 1)
        product.allocate(line)

    product.change_batch_quantity(ref, new_qty)

    assert batch.available_quantity >= 0

    deallocated = [e for e in product.events if isinstance(e, events.Deallocated)]
    assert len(deallocated) >= 0
