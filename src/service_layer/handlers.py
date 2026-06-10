from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Protocol

from sqlalchemy import text

from src.domain import events
from src.domain.commands import Allocate, ChangeBatchQuantity, Command, CreateBatch
from src.domain.model import Batch, OrderLine, Product

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.sql.elements import TextClause


class InvalidStockKeepingUnitError(Exception):
    pass


class ProductsRepository(Protocol):
    def get(self, stock_keeping_unit: str) -> Product | None: ...
    def add(self, product: Product) -> None: ...
    def get_by_batch_reference(self, batch_reference: str) -> Product: ...


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


def add_batch(cmd: CreateBatch, unit_of_work: AbstractUnitOfWork) -> None:
    with unit_of_work:
        product = unit_of_work.products.get(stock_keeping_unit=cmd.stock_keeping_unit)
        if product is None:
            product = Product(cmd.stock_keeping_unit, batches=[])
            unit_of_work.products.add(product)
        product.batches.append(
            Batch(cmd.reference, cmd.stock_keeping_unit, cmd.quantity, cmd.estimated_time_of_arrival)
        )
        unit_of_work.commit()


def allocate(cmd: Allocate, unit_of_work: AbstractUnitOfWork) -> None:
    line = OrderLine(cmd.order_id, cmd.stock_keeping_unit, cmd.quantity)
    with unit_of_work:
        product = unit_of_work.products.get(stock_keeping_unit=line.stock_keeping_unit)
        if product is None:
            raise InvalidStockKeepingUnitError(f"Invalid stock_keeping_unit {line.stock_keeping_unit}")
        product.allocate(line)
        unit_of_work.commit()


def reallocate(event: events.Deallocated, unit_of_work: AbstractUnitOfWork) -> None:
    allocate(Allocate(**asdict(event)), unit_of_work=unit_of_work)


def change_batch_quantity(cmd: ChangeBatchQuantity, unit_of_work: AbstractUnitOfWork) -> None:
    with unit_of_work:
        product = unit_of_work.products.get_by_batch_reference(batch_reference=cmd.reference)
        product.change_batch_quantity(reference=cmd.reference, quantity=cmd.quantity)
        unit_of_work.commit()


def send_out_of_stock_notification(
    event: events.OutOfStock,
    notifications: AbstractNotifications,
) -> None:
    notifications.send(
        "stock@made.com",
        f"Out of stock for {event.stock_keeping_unit}",
    )


def publish_allocated_event(
    event: events.Allocated,
    publish: Callable[[str, events.Allocated], Any],
) -> None:
    publish("line_allocated", event)


def add_allocation_to_read_model(
    event: events.Allocated,
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    with unit_of_work:
        unit_of_work.session.execute(
            text(
                "INSERT INTO allocations_view (order_id, stock_keeping_unit, batch_reference)"
                " VALUES (:order_id, :stock_keeping_unit, :batch_reference)"
            ),
            {
                "order_id": event.order_id,
                "stock_keeping_unit": event.stock_keeping_unit,
                "batch_reference": event.batch_reference,
            },
        )
        unit_of_work.commit()


def remove_allocation_from_read_model(
    event: events.Deallocated,
    unit_of_work: SqlAlchemyUnitOfWork,
) -> None:
    with unit_of_work:
        unit_of_work.session.execute(
            text(
                "DELETE FROM allocations_view  WHERE order_id = :order_id AND stock_keeping_unit = :stock_keeping_unit"
            ),
            {"order_id": event.order_id, "stock_keeping_unit": event.stock_keeping_unit},
        )
        unit_of_work.commit()


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
