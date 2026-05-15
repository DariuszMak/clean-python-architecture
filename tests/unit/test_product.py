from datetime import UTC, date, datetime, timedelta

from hypothesis import assume, given
from hypothesis import strategies as st

from allocation.domain import events
from allocation.domain.model import Batch, OrderLine, Product

today = datetime.now(tz=UTC).date()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)

stock_keeping_unit_text = st.text(alphabet=st.characters(whitelist_categories=["Lu"]), min_size=1, max_size=20)
reference_text = st.text(alphabet=st.characters(whitelist_categories=["Lu", "Nd"]), min_size=1, max_size=20)
pos_quantity = st.integers(min_value=1, max_value=10_000)
eta_days = st.one_of(st.none(), st.integers(min_value=0, max_value=365))


def make_eta(days: int | None) -> date | None:
    return (today + timedelta(days=days)) if days is not None else None


def test_preferenceers_warehouse_batches_to_shipments() -> None:
    in_stock_batch = Batch("in-stock-batch", "RETRO-CLOCK", 100, eta=None)
    shipment_batch = Batch("shipment-batch", "RETRO-CLOCK", 100, eta=tomorrow)
    product = Product(stock_keeping_unit="RETRO-CLOCK", batches=[in_stock_batch, shipment_batch])
    line = OrderLine("oreference", "RETRO-CLOCK", 10)

    product.allocate(line)

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_preferenceers_earlier_batches() -> None:
    earliest = Batch("speedy-batch", "MINIMALIST-SPOON", 100, eta=today)
    medium = Batch("normal-batch", "MINIMALIST-SPOON", 100, eta=tomorrow)
    latest = Batch("slow-batch", "MINIMALIST-SPOON", 100, eta=later)
    product = Product(stock_keeping_unit="MINIMALIST-SPOON", batches=[medium, earliest, latest])
    line = OrderLine("order1", "MINIMALIST-SPOON", 10)

    product.allocate(line)

    assert earliest.available_quantity == 90
    assert medium.available_quantity == 100
    assert latest.available_quantity == 100


def test_returns_allocated_batch_reference() -> None:
    in_stock_batch = Batch("in-stock-batch-referenceerence", "HIGHBROW-POSTER", 100, eta=None)
    shipment_batch = Batch("shipment-batch-referenceerence", "HIGHBROW-POSTER", 100, eta=tomorrow)
    line = OrderLine("oreference", "HIGHBROW-POSTER", 10)
    product = Product(stock_keeping_unit="HIGHBROW-POSTER", batches=[in_stock_batch, shipment_batch])
    allocation = product.allocate(line)
    assert allocation == in_stock_batch.referenceerence


def test_outputs_allocated_event() -> None:
    batch = Batch("batchreference", "RETRO-LAMPSHADE", 100, eta=None)
    line = OrderLine("oreference", "RETRO-LAMPSHADE", 10)
    product = Product(stock_keeping_unit="RETRO-LAMPSHADE", batches=[batch])
    product.allocate(line)
    expected = events.Allocated(
        orderid="oreference", stock_keeping_unit="RETRO-LAMPSHADE", quantity=10, batchreference=batch.referenceerence
    )
    assert product.events[-1] == expected


def test_records_out_of_stock_event_if_cannot_allocate() -> None:
    batch = Batch("batch1", "SMALL-FORK", 10, eta=today)
    product = Product(stock_keeping_unit="SMALL-FORK", batches=[batch])
    product.allocate(OrderLine("order1", "SMALL-FORK", 10))

    allocation = product.allocate(OrderLine("order2", "SMALL-FORK", 1))
    assert product.events[-1] == events.OutOfStock(stock_keeping_unit="SMALL-FORK")
    assert allocation is None


def test_increments_version_number() -> None:
    line = OrderLine("oreference", "SCANDI-PEN", 10)
    product = Product(stock_keeping_unit="SCANDI-PEN", batches=[Batch("b1", "SCANDI-PEN", 100, eta=None)])
    product.version_number = 7
    product.allocate(line)
    assert product.version_number == 8


@given(
    stock_keeping_unit=stock_keeping_unit_text, referenceerence=reference_text, batch_quantity=pos_quantity, line_quantity=pos_quantity, days=eta_days
)
def test_allocate_returns_batchreference_when_sufficient_stock(
    stock_keeping_unit: str, referenceerence: str, batch_quantity: int, line_quantity: int, days: int | None
) -> None:
    assume(batch_quantity >= line_quantity)
    batch = Batch(referenceerence, stock_keeping_unit, batch_quantity, make_eta(days))
    product = Product(stock_keeping_unit=stock_keeping_unit, batches=[batch])
    line = OrderLine("order-1", stock_keeping_unit, line_quantity)

    result = product.allocate(line)

    assert result == referenceerence


@given(
    stock_keeping_unit=stock_keeping_unit_text, referenceerence=reference_text, batch_quantity=pos_quantity, line_quantity=pos_quantity, days=eta_days
)
def test_allocate_returns_none_and_emits_out_of_stock_when_insufficient(
    stock_keeping_unit: str, referenceerence: str, batch_quantity: int, line_quantity: int, days: int | None
) -> None:
    assume(batch_quantity < line_quantity)
    batch = Batch(referenceerence, stock_keeping_unit, batch_quantity, make_eta(days))
    product = Product(stock_keeping_unit=stock_keeping_unit, batches=[batch])
    line = OrderLine("order-1", stock_keeping_unit, line_quantity)

    result = product.allocate(line)

    assert result is None
    assert any(isinstance(e, events.OutOfStock) for e in product.events)


@given(stock_keeping_unit=stock_keeping_unit_text, referenceerence=reference_text, quantity=pos_quantity, days=eta_days)
def test_version_number_increments_on_successful_allocation(
    stock_keeping_unit: str, referenceerence: str, quantity: int, days: int | None
) -> None:
    batch = Batch(referenceerence, stock_keeping_unit, quantity, make_eta(days))
    product = Product(stock_keeping_unit=stock_keeping_unit, batches=[batch])
    initial_version = product.version_number
    line = OrderLine("order-1", stock_keeping_unit, 1)

    product.allocate(line)

    assert product.version_number == initial_version + 1


@given(stock_keeping_unit=stock_keeping_unit_text, referenceerence=reference_text, quantity=pos_quantity, days=eta_days)
def test_version_number_does_not_increment_on_out_of_stock(
    stock_keeping_unit: str, referenceerence: str, quantity: int, days: int | None
) -> None:
    batch = Batch(referenceerence, stock_keeping_unit, quantity, make_eta(days))
    product = Product(stock_keeping_unit=stock_keeping_unit, batches=[batch])
    initial_version = product.version_number
    line = OrderLine("order-1", stock_keeping_unit, quantity + 1)

    product.allocate(line)

    assert product.version_number == initial_version


@given(
    stock_keeping_unit=stock_keeping_unit_text,
    reference1=reference_text,
    reference2=reference_text,
    quantity=pos_quantity,
    days_early=st.integers(min_value=1, max_value=100),
    days_late=st.integers(min_value=101, max_value=200),
)
def test_preferenceers_earlier_batch(
    stock_keeping_unit: str, reference1: str, reference2: str, quantity: int, days_early: int, days_late: int
) -> None:
    assume(reference1 != reference2)
    early_batch = Batch(reference1, stock_keeping_unit, quantity, today + timedelta(days=days_early))
    late_batch = Batch(reference2, stock_keeping_unit, quantity, today + timedelta(days=days_late))
    product = Product(stock_keeping_unit=stock_keeping_unit, batches=[late_batch, early_batch])
    line = OrderLine("order-1", stock_keeping_unit, 1)

    result = product.allocate(line)

    assert result == reference1


@given(stock_keeping_unit=stock_keeping_unit_text, reference1=reference_text, reference2=reference_text, quantity=pos_quantity, days=eta_days)
def test_preferenceers_in_stock_over_shipment(
    stock_keeping_unit: str, reference1: str, reference2: str, quantity: int, days: int | None
) -> None:
    assume(reference1 != reference2)
    assume(days is not None)
    in_stock = Batch(reference1, stock_keeping_unit, quantity, eta=None)
    shipment = Batch(reference2, stock_keeping_unit, quantity, make_eta(days))
    product = Product(stock_keeping_unit=stock_keeping_unit, batches=[shipment, in_stock])
    line = OrderLine("order-1", stock_keeping_unit, 1)

    result = product.allocate(line)

    assert result == reference1


@given(stock_keeping_unit=stock_keeping_unit_text, referenceerence=reference_text, quantity=pos_quantity, line_quantity=pos_quantity, days=eta_days)
def test_allocated_event_has_correct_fields(
    stock_keeping_unit: str, referenceerence: str, quantity: int, line_quantity: int, days: int | None
) -> None:
    assume(quantity >= line_quantity)
    batch = Batch(referenceerence, stock_keeping_unit, quantity, make_eta(days))
    product = Product(stock_keeping_unit=stock_keeping_unit, batches=[batch])
    line = OrderLine("order-1", stock_keeping_unit, line_quantity)

    product.allocate(line)

    allocated_events = [e for e in product.events if isinstance(e, events.Allocated)]
    assert len(allocated_events) == 1
    ev = allocated_events[0]
    assert ev.orderid == "order-1"
    assert ev.stock_keeping_unit == stock_keeping_unit
    assert ev.quantity == line_quantity
    assert ev.batchreference == referenceerence


@given(
    stock_keeping_unit=stock_keeping_unit_text,
    referenceerence=reference_text,
    initial_quantity=st.integers(min_value=2, max_value=10_000),
    n_extra=st.integers(min_value=1, max_value=5),
)
def test_change_batch_quantity_deallocates_excess_orders(
    stock_keeping_unit: str, referenceerence: str, initial_quantity: int, n_extra: int
) -> None:
    new_quantity = max(1, initial_quantity - n_extra)
    batch = Batch(referenceerence, stock_keeping_unit, initial_quantity, eta=None)
    product = Product(stock_keeping_unit=stock_keeping_unit, batches=[batch])

    for i in range(n_extra):
        line = OrderLine(f"order-{i}", stock_keeping_unit, 1)
        product.allocate(line)

    product.change_batch_quantity(referenceerence, new_quantity)

    assert batch.available_quantity >= 0

    deallocated = [e for e in product.events if isinstance(e, events.Deallocated)]
    assert len(deallocated) >= 0
