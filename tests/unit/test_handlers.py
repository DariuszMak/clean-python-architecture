from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from adapters.notifications import AbstractNotifications
from adapters.repository import AbstractRepository
from bootstrap import bootstrap
from domain.commands import Allocate, ChangeBatchQuantity, CreateBatch
from service_layer.handlers import InvalidStockKeepingUnitError
from service_layer.unit_of_work import AbstractUnitOfWork

if TYPE_CHECKING:
    from collections.abc import Iterable


stock_keeping_unit_text = st.text(
    alphabet=st.characters(whitelist_categories=["Lu"]),
    min_size=1,
    max_size=20,
)

reference_text = st.text(
    alphabet=st.characters(whitelist_categories=["Lu", "Nd"]),
    min_size=1,
    max_size=20,
)

order_text = st.text(
    alphabet=st.characters(whitelist_categories=["Lu", "Nd"]),
    min_size=1,
    max_size=20,
)

pos_quantity = st.integers(min_value=1, max_value=10_000)

estimated_time_of_arrival_days = st.one_of(
    st.none(),
    st.integers(min_value=0, max_value=365),
)


class FakeRepository(AbstractRepository):  # type: ignore[misc]
    def __init__(self, products: Iterable[Any]) -> None:
        super().__init__()
        self._products = set(products)

    def _add(self, product: Any) -> None:
        self._products.add(product)

    def _get(self, stock_keeping_unit: str) -> Any:
        return next((p for p in self._products if p.stock_keeping_unit == stock_keeping_unit), None)

    def _get_by_batch_reference(self, batch_reference: str) -> Any:
        return next(
            (p for p in self._products for b in p.batches if b.reference == batch_reference),
            None,
        )


class FakeUnitOfWork(AbstractUnitOfWork):  # type: ignore[misc]
    def __init__(self) -> None:
        self.products: FakeRepository = FakeRepository([])
        self.committed: bool = False

    def _commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


class FakeNotifications(AbstractNotifications):  # type: ignore[misc]
    def __init__(self) -> None:
        self.sent: dict[str, list[str]] = defaultdict(list)

    def send(self, destination: str, message: str) -> None:
        self.sent[destination].append(message)


def bootstrap_test_app() -> Any:
    return bootstrap(
        start_orm=False,
        unit_of_work=FakeUnitOfWork(),
        notifications=FakeNotifications(),
        publish=lambda *_: None,
    )


def make_estimated_time_of_arrival_str(days: int | None) -> str | None:
    if days is None:
        return None
    return (datetime.now(tz=UTC).date() + timedelta(days=days)).isoformat()


class TestAddBatch:
    def test_for_new_product(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(CreateBatch("b1", "CRUNCHY-ARMCHAIR", 100, None))
        assert bus.unit_of_work.products.get("CRUNCHY-ARMCHAIR") is not None
        assert bus.unit_of_work.committed

    def test_for_existing_product(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(CreateBatch("b1", "GARISH-RUG", 100, None))
        bus.handle(CreateBatch("b2", "GARISH-RUG", 99, None))
        assert "b2" in [b.reference for b in bus.unit_of_work.products.get("GARISH-RUG").batches]


class TestAllocate:
    def test_allocates(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(CreateBatch("batch1", "COMPLICATED-LAMP", 100, None))
        bus.handle(Allocate("o1", "COMPLICATED-LAMP", 10))
        [batch] = bus.unit_of_work.products.get("COMPLICATED-LAMP").batches
        assert batch.available_quantity == 90

    def test_errors_for_invalid_stock_keeping_unit(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(CreateBatch("b1", "AREALSTOCKKEEPINGUNIT", 100, None))

        with pytest.raises(
            InvalidStockKeepingUnitError, match="Invalid stock_keeping_unit NONEXISTENTSTOCKKEEPINGUNIT"
        ):
            bus.handle(Allocate("o1", "NONEXISTENTSTOCKKEEPINGUNIT", 10))

    def test_commits(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(CreateBatch("b1", "OMINOUS-MIRROR", 100, None))
        bus.handle(Allocate("o1", "OMINOUS-MIRROR", 10))
        assert bus.unit_of_work.committed

    def test_sends_email_on_out_of_stock_error(self) -> None:
        fake_notifs = FakeNotifications()
        bus = bootstrap(
            start_orm=False,
            unit_of_work=FakeUnitOfWork(),
            notifications=fake_notifs,
            publish=lambda *_: None,
        )
        bus.handle(CreateBatch("b1", "POPULAR-CURTAINS", 9, None))
        bus.handle(Allocate("o1", "POPULAR-CURTAINS", 10))
        assert fake_notifs.sent["stock@made.com"] == [
            "Out of stock for POPULAR-CURTAINS",
        ]


class TestChangeBatchQuantity:
    def test_changes_available_quantity(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(CreateBatch("batch1", "ADORABLE-SETTEE", 100, None))
        [batch] = bus.unit_of_work.products.get(stock_keeping_unit="ADORABLE-SETTEE").batches
        assert batch.available_quantity == 100

        bus.handle(ChangeBatchQuantity("batch1", 50))
        assert batch.available_quantity == 50

    def test_reallocates_if_necessary(self) -> None:
        bus = bootstrap_test_app()
        history = [
            CreateBatch("batch1", "INDIFFERENT-TABLE", 50, None),
            CreateBatch(
                "batch2",
                "INDIFFERENT-TABLE",
                50,
                datetime.now(tz=UTC).date(),
            ),
            Allocate("order1", "INDIFFERENT-TABLE", 20),
            Allocate("order2", "INDIFFERENT-TABLE", 20),
        ]
        for msg in history:
            bus.handle(msg)

        [batch1, batch2] = bus.unit_of_work.products.get(stock_keeping_unit="INDIFFERENT-TABLE").batches

        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        bus.handle(ChangeBatchQuantity("batch1", 25))

        assert batch1.available_quantity == 5
        assert batch2.available_quantity == 30


@given(
    reference=reference_text,
    stock_keeping_unit=stock_keeping_unit_text,
    quantity=pos_quantity,
    days=estimated_time_of_arrival_days,
)
def test_create_batch_creates_product_if_not_exists(
    reference: str,
    stock_keeping_unit: str,
    quantity: int,
    days: int | None,
) -> None:
    bus = bootstrap_test_app()

    estimated_time_of_arrival_date = datetime.now(tz=UTC).date() + timedelta(days=days) if days is not None else None

    bus.handle(CreateBatch(reference, stock_keeping_unit, quantity, estimated_time_of_arrival_date))

    assert bus.unit_of_work.products.get(stock_keeping_unit) is not None


@given(
    reference=reference_text,
    stock_keeping_unit=stock_keeping_unit_text,
    quantity=pos_quantity,
    days=estimated_time_of_arrival_days,
)
def test_create_batch_commits(
    reference: str,
    stock_keeping_unit: str,
    quantity: int,
    days: int | None,
) -> None:
    bus = bootstrap_test_app()

    estimated_time_of_arrival_date = datetime.now(tz=UTC).date() + timedelta(days=days) if days is not None else None

    bus.handle(CreateBatch(reference, stock_keeping_unit, quantity, estimated_time_of_arrival_date))

    assert bus.unit_of_work.committed


@given(
    reference=reference_text,
    stock_keeping_unit=stock_keeping_unit_text,
    batch_quantity=pos_quantity,
    line_quantity=pos_quantity,
    order_id=order_text,
    days=estimated_time_of_arrival_days,
)
def test_allocate_reduces_available_quantity(
    reference: str,
    stock_keeping_unit: str,
    batch_quantity: int,
    line_quantity: int,
    order_id: str,
    days: int | None,
) -> None:
    assume(batch_quantity >= line_quantity)

    bus = bootstrap_test_app()

    estimated_time_of_arrival_date = datetime.now(tz=UTC).date() + timedelta(days=days) if days is not None else None

    bus.handle(CreateBatch(reference, stock_keeping_unit, batch_quantity, estimated_time_of_arrival_date))
    bus.handle(Allocate(order_id, stock_keeping_unit, line_quantity))

    [batch] = bus.unit_of_work.products.get(stock_keeping_unit).batches

    assert batch.available_quantity == batch_quantity - line_quantity


@given(
    reference=reference_text,
    stock_keeping_unit=stock_keeping_unit_text,
    batch_quantity=pos_quantity,
    line_quantity=pos_quantity,
    order_id=order_text,
    days=estimated_time_of_arrival_days,
)
def test_allocate_commits_on_success(
    reference: str,
    stock_keeping_unit: str,
    batch_quantity: int,
    line_quantity: int,
    order_id: str,
    days: int | None,
) -> None:
    assume(batch_quantity >= line_quantity)

    bus = bootstrap_test_app()

    estimated_time_of_arrival_date = datetime.now(tz=UTC).date() + timedelta(days=days) if days is not None else None

    bus.handle(CreateBatch(reference, stock_keeping_unit, batch_quantity, estimated_time_of_arrival_date))

    bus.unit_of_work.committed = False

    bus.handle(Allocate(order_id, stock_keeping_unit, line_quantity))

    assert bus.unit_of_work.committed


@given(stock_keeping_unit=stock_keeping_unit_text, order_id=order_text, quantity=pos_quantity)
def test_allocate_raises_for_unknown_stock_keeping_unit(
    stock_keeping_unit: str,
    order_id: str,
    quantity: int,
) -> None:
    bus = bootstrap_test_app()

    with pytest.raises(InvalidStockKeepingUnitError, match=f"Invalid stock_keeping_unit {stock_keeping_unit}"):
        bus.handle(Allocate(order_id, stock_keeping_unit, quantity))


@given(
    reference=reference_text,
    stock_keeping_unit=stock_keeping_unit_text,
    quantity=pos_quantity,
    new_quantity=pos_quantity,
    days=estimated_time_of_arrival_days,
)
def test_change_batch_quantity_updates_available(
    reference: str,
    stock_keeping_unit: str,
    quantity: int,
    new_quantity: int,
    days: int | None,
) -> None:
    bus = bootstrap_test_app()

    estimated_time_of_arrival_date = datetime.now(tz=UTC).date() + timedelta(days=days) if days is not None else None

    bus.handle(CreateBatch(reference, stock_keeping_unit, quantity, estimated_time_of_arrival_date))
    bus.handle(ChangeBatchQuantity(reference, new_quantity))

    [batch] = bus.unit_of_work.products.get(stock_keeping_unit).batches

    assert batch._purchased_quantity == new_quantity


@given(
    reference=reference_text,
    stock_keeping_unit=stock_keeping_unit_text,
    batch_quantity=pos_quantity,
    line_quantity=pos_quantity,
    order_id=order_text,
)
def test_out_of_stock_sends_email(
    reference: str,
    stock_keeping_unit: str,
    batch_quantity: int,
    line_quantity: int,
    order_id: str,
) -> None:
    assume(batch_quantity < line_quantity)

    fake_notifs = FakeNotifications()

    bus = bootstrap(
        start_orm=False,
        unit_of_work=FakeUnitOfWork(),
        notifications=fake_notifs,
        publish=lambda *_: None,
    )

    bus.handle(CreateBatch(reference, stock_keeping_unit, batch_quantity, None))
    bus.handle(Allocate(order_id, stock_keeping_unit, line_quantity))

    assert f"Out of stock for {stock_keeping_unit}" in fake_notifs.sent.get("stock@made.com", [])


@given(
    reference1=reference_text,
    reference2=reference_text,
    stock_keeping_unit=stock_keeping_unit_text,
    quantity=pos_quantity,
    line_quantity=pos_quantity,
    order_id=order_text,
    days1=st.integers(min_value=1, max_value=100),
    days2=st.integers(min_value=101, max_value=200),
)
def test_reallocate_moves_order_to_later_batch_when_earlier_shrinks(
    reference1: str,
    reference2: str,
    stock_keeping_unit: str,
    quantity: int,
    line_quantity: int,
    order_id: str,
    days1: int,
    days2: int,
) -> None:
    assume(reference1 != reference2)
    assume(quantity >= line_quantity)
    assume(quantity > line_quantity)

    bus = bootstrap_test_app()

    today = datetime.now(tz=UTC).date()
    estimated_time_of_arrival1 = today + timedelta(days=days1)
    estimated_time_of_arrival2 = today + timedelta(days=days2)

    bus.handle(CreateBatch(reference1, stock_keeping_unit, quantity, estimated_time_of_arrival1))
    bus.handle(CreateBatch(reference2, stock_keeping_unit, quantity, estimated_time_of_arrival2))
    bus.handle(Allocate(order_id, stock_keeping_unit, line_quantity))

    new_quantity = line_quantity - 1

    bus.handle(ChangeBatchQuantity(reference1, new_quantity))

    product = bus.unit_of_work.products.get(stock_keeping_unit)

    b2 = next(b for b in product.batches if b.reference == reference2)

    assert b2.available_quantity == quantity - line_quantity
