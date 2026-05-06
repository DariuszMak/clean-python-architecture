

from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Protocol

from sqlalchemy import text

from allocation.domain import events
from allocation.domain.commands import Allocate, ChangeBatchQuantity, Command, CreateBatch
from allocation.domain.model import Batch, OrderLine, Product

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.sql.elements import TextClause


class InvalidSkuError(Exception):
    pass


class ProductsRepository(Protocol):
    def get(self, sku: str) -> Product | None: ...
    def add(self, product: Product) -> None: ...
    def get_by_batchref(self, batchref: str) -> Product: ...


class AbstractUnitOfWork(Protocol):
    products: ProductsRepository

    def __enter__(self) -> AbstractUnitOfWork: ...
    def __exit__(self, *args: Any) -> None: ...
    def commit(self) -> None: ...


class Session(Protocol):
    def execute(self, _: TextClause, __: dict[str, Any]) -> Any: ...


class SqlAlchemyUnitOfWork(AbstractUnitOfWork, Protocol):
    session: Session


class AbstractNotifications(Protocol):
    def send(self, _: str, message: str) -> None: ...


def add_batch(cmd: CreateBatch, uow: AbstractUnitOfWork) -> None:
    with uow:
        product = uow.products.get(sku=cmd.sku)
        if product is None:
            product = Product(cmd.sku, batches=[])
            uow.products.add(product)
        product.batches.append(Batch(cmd.ref, cmd.sku, cmd.qty, cmd.eta))
        uow.commit()


def allocate(cmd: Allocate, uow: AbstractUnitOfWork) -> None:
    line = OrderLine(cmd.orderid, cmd.sku, cmd.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSkuError(f"Invalid sku {line.sku}")
        product.allocate(line)
        uow.commit()


def reallocate(event: events.Deallocated, uow: AbstractUnitOfWork) -> None:
    allocate(Allocate(**asdict(event)), uow=uow)


def change_batch_quantity(cmd: ChangeBatchQuantity, uow: AbstractUnitOfWork) -> None:
    with uow:
        product = uow.products.get_by_batchref(batchref=cmd.ref)
        product.change_batch_quantity(ref=cmd.ref, qty=cmd.qty)
        uow.commit()


def send_out_of_stock_notification(
    event: events.OutOfStock,
    notifications: AbstractNotifications,
) -> None:
    notifications.send(
        "stock@made.com",
        f"Out of stock for {event.sku}",
    )


def publish_allocated_event(
    event: events.Allocated,
    publish: Callable[[str, events.Allocated], Any],
) -> None:
    publish("line_allocated", event)


def add_allocation_to_read_model(
    event: events.Allocated,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    with uow:
        uow.session.execute(
            text("INSERT INTO allocations_view (orderid, sku, batchref) VALUES (:orderid, :sku, :batchref)"),
            {"orderid": event.orderid, "sku": event.sku, "batchref": event.batchref},
        )
        uow.commit()


def remove_allocation_from_read_model(
    event: events.Deallocated,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    with uow:
        uow.session.execute(
            text("DELETE FROM allocations_view  WHERE orderid = :orderid AND sku = :sku"),
            {"orderid": event.orderid, "sku": event.sku},
        )
        uow.commit()


EVENT_HANDLERS: dict[type[events.Event], list[Callable[..., Any]]] = {
    events.Allocated: [publish_allocated_event, add_allocation_to_read_model],
    events.Deallocated: [remove_allocation_from_read_model, reallocate],
    events.OutOfStock: [send_out_of_stock_notification],
}

COMMAND_HANDLERS: dict[type[Command], Callable[..., Any]] = {
    Allocate: allocate,
    CreateBatch: add_batch,
    ChangeBatchQuantity: change_batch_quantity,
}
