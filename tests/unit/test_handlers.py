from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from allocation.adapters.notifications import AbstractNotifications
from allocation.adapters.repository import AbstractRepository
from allocation.bootstrap import bootstrap
from allocation.domain.commands import Allocate, ChangeBatchQuantity, CreateBatch
from allocation.service_layer.handlers import InvalidSkuError
from allocation.service_layer.unit_of_work import AbstractUnitOfWork

if TYPE_CHECKING:
    from collections.abc import Iterable


sku_text = st.text(
    alphabet=st.characters(whitelist_categories=["Lu"]),
    min_size=1,
    max_size=20,
)

ref_text = st.text(
    alphabet=st.characters(whitelist_categories=["Lu", "Nd"]),
    min_size=1,
    max_size=20,
)

order_text = st.text(
    alphabet=st.characters(whitelist_categories=["Lu", "Nd"]),
    min_size=1,
    max_size=20,
)

pos_qty = st.integers(min_value=1, max_value=10_000)

eta_days = st.one_of(
    st.none(),
    st.integers(min_value=0, max_value=365),
)


class FakeRepository(AbstractRepository):
    def __init__(self, products: Iterable[Any]) -> None:
        super().__init__()
        self._products = set(products)

    def _add(self, product: Any) -> None:
        self._products.add(product)

    def _get(self, sku: str) -> Any:
        return next((p for p in self._products if p.sku == sku), None)

    def _get_by_batchref(self, batchref: str) -> Any:
        return next(
            (p for p in self._products for b in p.batches if b.reference == batchref),
            None,
        )


class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self) -> None:
        self.products: FakeRepository = FakeRepository([])
        self.committed: bool = False

    def _commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        pass


class FakeNotifications(AbstractNotifications):
    def __init__(self) -> None:
        self.sent: dict[str, list[str]] = defaultdict(list)

    def send(self, destination: str, message: str) -> None:
        self.sent[destination].append(message)


def bootstrap_test_app() -> Any:
    return bootstrap(
        start_orm=False,
        uow=FakeUnitOfWork(),
        notifications=FakeNotifications(),
        publish=lambda *_: None,
    )


def make_eta_str(days: int | None) -> str | None:
    if days is None:
        return None
    return (datetime.now(tz=UTC).date() + timedelta(days=days)).isoformat()


class TestAddBatch:
    def test_for_new_product(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(CreateBatch("b1", "CRUNCHY-ARMCHAIR", 100, None))
        assert bus.uow.products.get("CRUNCHY-ARMCHAIR") is not None
        assert bus.uow.committed

    def test_for_existing_product(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(CreateBatch("b1", "GARISH-RUG", 100, None))
        bus.handle(CreateBatch("b2", "GARISH-RUG", 99, None))
        assert "b2" in [b.reference for b in bus.uow.products.get("GARISH-RUG").batches]


class TestAllocate:
    def test_allocates(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(CreateBatch("batch1", "COMPLICATED-LAMP", 100, None))
        bus.handle(Allocate("o1", "COMPLICATED-LAMP", 10))
        [batch] = bus.uow.products.get("COMPLICATED-LAMP").batches
        assert batch.available_quantity == 90

    def test_errors_for_invalid_sku(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(CreateBatch("b1", "AREALSKU", 100, None))

        with pytest.raises(InvalidSkuError, match="Invalid sku NONEXISTENTSKU"):
            bus.handle(Allocate("o1", "NONEXISTENTSKU", 10))

    def test_commits(self) -> None:
        bus = bootstrap_test_app()
        bus.handle(CreateBatch("b1", "OMINOUS-MIRROR", 100, None))
        bus.handle(Allocate("o1", "OMINOUS-MIRROR", 10))
        assert bus.uow.committed

    def test_sends_email_on_out_of_stock_error(self) -> None:
        fake_notifs = FakeNotifications()
        bus = bootstrap(
            start_orm=False,
            uow=FakeUnitOfWork(),
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
        [batch] = bus.uow.products.get(sku="ADORABLE-SETTEE").batches
        assert batch.available_quantity == 100

        bus.handle(ChangeBatchQuantity("batch1", 50))
        assert batch.available_quantity == 50

    def test_reallocates_if_necessary(self) -> None:
        bus = bootstrap_test_app()
        history = [
            CreateBatch("batch1", "INDIFFERENT-TABLE", 50, None),
            CreateBatch("batch2", "INDIFFERENT-TABLE", 50, datetime.now(tz=UTC).date()),
            Allocate("order1", "INDIFFERENT-TABLE", 20),
            Allocate("order2", "INDIFFERENT-TABLE", 20),
        ]
        for msg in history:
            bus.handle(msg)
        [batch1, batch2] = bus.uow.products.get(sku="INDIFFERENT-TABLE").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        bus.handle(ChangeBatchQuantity("batch1", 25))

        assert batch1.available_quantity == 5
        assert batch2.available_quantity == 30


@given(ref=ref_text, sku=sku_text, qty=pos_qty, days=eta_days)
def test_create_batch_creates_product_if_not_exists(ref: str, sku: str, qty: int, days: int | None) -> None:
    bus = bootstrap_test_app()
    make_eta_str(days)
    eta_date = (datetime.now(tz=UTC).date() + timedelta(days=days)) if days is not None else None

    bus.handle(CreateBatch(ref, sku, qty, eta_date))

    assert bus.uow.products.get(sku) is not None


@given(ref=ref_text, sku=sku_text, qty=pos_qty, days=eta_days)
def test_create_batch_commits(ref: str, sku: str, qty: int, days: int | None) -> None:
    bus = bootstrap_test_app()
    eta_date = (datetime.now(tz=UTC).date() + timedelta(days=days)) if days is not None else None

    bus.handle(CreateBatch(ref, sku, qty, eta_date))

    assert bus.uow.committed


@given(
    ref=ref_text,
    sku=sku_text,
    batch_qty=pos_qty,
    line_qty=pos_qty,
    orderid=order_text,
    days=eta_days,
)
def test_allocate_reduces_available_quantity(
    ref: str, sku: str, batch_qty: int, line_qty: int, orderid: str, days: int | None
) -> None:
    assume(batch_qty >= line_qty)
    bus = bootstrap_test_app()
    eta_date = (datetime.now(tz=UTC).date() + timedelta(days=days)) if days is not None else None

    bus.handle(CreateBatch(ref, sku, batch_qty, eta_date))
    bus.handle(Allocate(orderid, sku, line_qty))

    [batch] = bus.uow.products.get(sku).batches
    assert batch.available_quantity == batch_qty - line_qty


@given(
    ref=ref_text,
    sku=sku_text,
    batch_qty=pos_qty,
    line_qty=pos_qty,
    orderid=order_text,
    days=eta_days,
)
def test_allocate_commits_on_success(
    ref: str, sku: str, batch_qty: int, line_qty: int, orderid: str, days: int | None
) -> None:
    assume(batch_qty >= line_qty)
    bus = bootstrap_test_app()
    eta_date = (datetime.now(tz=UTC).date() + timedelta(days=days)) if days is not None else None

    bus.handle(CreateBatch(ref, sku, batch_qty, eta_date))
    bus.uow.committed = False
    bus.handle(Allocate(orderid, sku, line_qty))

    assert bus.uow.committed


@given(sku=sku_text, orderid=order_text, qty=pos_qty)
def test_allocate_raises_for_unknown_sku(sku: str, orderid: str, qty: int) -> None:
    bus = bootstrap_test_app()

    with pytest.raises(InvalidSkuError, match=f"Invalid sku {sku}"):
        bus.handle(Allocate(orderid, sku, qty))


@given(ref=ref_text, sku=sku_text, qty=pos_qty, new_qty=pos_qty, days=eta_days)
def test_change_batch_quantity_updates_available(ref: str, sku: str, qty: int, new_qty: int, days: int | None) -> None:
    bus = bootstrap_test_app()
    eta_date = (datetime.now(tz=UTC).date() + timedelta(days=days)) if days is not None else None

    bus.handle(CreateBatch(ref, sku, qty, eta_date))
    bus.handle(ChangeBatchQuantity(ref, new_qty))

    [batch] = bus.uow.products.get(sku).batches
    assert batch._purchased_quantity == new_qty


@given(
    ref=ref_text,
    sku=sku_text,
    batch_qty=pos_qty,
    line_qty=pos_qty,
    orderid=order_text,
)
def test_out_of_stock_sends_email(ref: str, sku: str, batch_qty: int, line_qty: int, orderid: str) -> None:
    assume(batch_qty < line_qty)
    fake_notifs = FakeNotifications()
    bus = bootstrap(
        start_orm=False,
        uow=FakeUnitOfWork(),
        notifications=fake_notifs,
        publish=lambda *_: None,
    )

    bus.handle(CreateBatch(ref, sku, batch_qty, None))
    bus.handle(Allocate(orderid, sku, line_qty))

    assert f"Out of stock for {sku}" in fake_notifs.sent.get("stock@made.com", [])


@given(
    ref1=ref_text,
    ref2=ref_text,
    sku=sku_text,
    qty=pos_qty,
    line_qty=pos_qty,
    orderid=order_text,
    days1=st.integers(min_value=1, max_value=100),
    days2=st.integers(min_value=101, max_value=200),
)
def test_reallocate_moves_order_to_later_batch_when_earlier_shrinks(
    ref1: str,
    ref2: str,
    sku: str,
    qty: int,
    line_qty: int,
    orderid: str,
    days1: int,
    days2: int,
) -> None:
    assume(ref1 != ref2)
    assume(qty >= line_qty)
    assume(qty > line_qty)

    bus = bootstrap_test_app()
    today = datetime.now(tz=UTC).date()
    eta1 = today + timedelta(days=days1)
    eta2 = today + timedelta(days=days2)

    bus.handle(CreateBatch(ref1, sku, qty, eta1))
    bus.handle(CreateBatch(ref2, sku, qty, eta2))
    bus.handle(Allocate(orderid, sku, line_qty))

    new_qty = line_qty - 1
    bus.handle(ChangeBatchQuantity(ref1, new_qty))

    product = bus.uow.products.get(sku)
    b2 = next(b for b in product.batches if b.reference == ref2)
    assert b2.available_quantity == qty - line_qty
