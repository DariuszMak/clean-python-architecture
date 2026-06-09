import threading
import time
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import text

from domain.model import OrderLine
from service_layer.unit_of_work import SqlAlchemyUnitOfWork
from tests.random_references import random_batch_reference, random_order_id, random_stock_keeping_unit

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, sessionmaker

pytestmark = pytest.mark.usefixtures("mappers")


def insert_batch(
    session: Session,
    reference: str,
    stock_keeping_unit: str,
    quantity: int,
    estimated_time_of_arrival: Any,
    product_version: int = 1,
) -> None:
    session.execute(
        text("INSERT INTO products (stock_keeping_unit, version_number) VALUES (:stock_keeping_unit, :version)"),
        {"stock_keeping_unit": stock_keeping_unit, "version": product_version},
    )
    session.execute(
        text(
            "INSERT INTO batches (reference, stock_keeping_unit, _purchased_quantity, estimated_time_of_arrival)"
            " VALUES (:reference, :stock_keeping_unit, :quantity, :estimated_time_of_arrival)"
        ),
        {
            "reference": reference,
            "stock_keeping_unit": stock_keeping_unit,
            "quantity": quantity,
            "estimated_time_of_arrival": estimated_time_of_arrival,
        },
    )


def get_allocated_batch_reference(session: Session, order_id: str, stock_keeping_unit: str) -> str:
    [[orderline_id]] = session.execute(
        text("SELECT id FROM order_lines WHERE order_id=:order_id AND stock_keeping_unit=:stock_keeping_unit"),
        {"order_id": order_id, "stock_keeping_unit": stock_keeping_unit},
    )
    [[batch_reference]] = session.execute(
        text(
            "SELECT b.reference FROM allocations JOIN batches AS b ON batch_id = b.id WHERE orderline_id=:orderline_id"
        ),
        {"orderline_id": orderline_id},
    )
    return str(batch_reference)


def test_unit_of_work_can_retrieve_a_batch_and_allocate_to_it(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    session = sqlite_session_factory()
    insert_batch(session, "batch1", "HIPSTER-WORKBENCH", 100, None)
    session.commit()

    unit_of_work = SqlAlchemyUnitOfWork(sqlite_session_factory)
    with unit_of_work:
        product = unit_of_work.products.get(stock_keeping_unit="HIPSTER-WORKBENCH")
        line = OrderLine("o1", "HIPSTER-WORKBENCH", 10)
        product.allocate(line)
        unit_of_work.commit()

    batch_reference = get_allocated_batch_reference(session, "o1", "HIPSTER-WORKBENCH")
    assert batch_reference == "batch1"


def test_rolls_back_uncommitted_work_by_default(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    unit_of_work = SqlAlchemyUnitOfWork(sqlite_session_factory)
    with unit_of_work:
        insert_batch(unit_of_work.session, "batch1", "MEDIUM-PLINTH", 100, None)

    new_session = sqlite_session_factory()
    rows = list(new_session.execute(text('SELECT * FROM "batches"')))
    assert rows == []


def test_rolls_back_on_error(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    class MyError(Exception):
        pass

    unit_of_work = SqlAlchemyUnitOfWork(sqlite_session_factory)

    with unit_of_work:
        insert_batch(unit_of_work.session, "batch1", "LARGE-FORK", 100, None)
        with pytest.raises(MyError):
            raise MyError

    new_session = sqlite_session_factory()
    rows = list(new_session.execute(text('SELECT * FROM "batches"')))

    assert rows == []


def try_to_allocate(
    order_id: str,
    stock_keeping_unit: str,
    exceptions: list[Exception],
    session_factory: sessionmaker[Session],
) -> None:
    line = OrderLine(order_id, stock_keeping_unit, 10)
    try:
        with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
            product = unit_of_work.products.get(stock_keeping_unit=stock_keeping_unit)
            product.allocate(line)
            time.sleep(0.2)
            unit_of_work.commit()
    except Exception as e:
        exceptions.append(e)


def test_concurrent_updates_to_version_are_not_allowed(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    stock_keeping_unit, batch = random_stock_keeping_unit(), random_batch_reference()
    session = postgres_session_factory()
    insert_batch(session, batch, stock_keeping_unit, 100, estimated_time_of_arrival=None, product_version=1)
    session.commit()

    order1, order2 = random_order_id("1"), random_order_id("2")
    exceptions: list[Exception] = []

    def try_to_allocate_order1() -> None:
        return try_to_allocate(order1, stock_keeping_unit, exceptions, postgres_session_factory)

    def try_to_allocate_order2() -> None:
        return try_to_allocate(order2, stock_keeping_unit, exceptions, postgres_session_factory)

    thread1 = threading.Thread(target=try_to_allocate_order1)
    thread2 = threading.Thread(target=try_to_allocate_order2)
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()

    [[version]] = session.execute(
        text("SELECT version_number FROM products WHERE stock_keeping_unit=:stock_keeping_unit"),
        {"stock_keeping_unit": stock_keeping_unit},
    )
    assert version == 2
    [exception] = exceptions
    assert "could not serialize access due to concurrent update" in str(exception)

    orders = list(
        session.execute(
            text(
                "SELECT order_id FROM allocations"
                " JOIN batches ON allocations.batch_id = batches.id"
                " JOIN order_lines ON allocations.orderline_id = order_lines.id"
                " WHERE order_lines.stock_keeping_unit=:stock_keeping_unit"
            ),
            {"stock_keeping_unit": stock_keeping_unit},
        )
    )
    assert len(orders) == 1
    with SqlAlchemyUnitOfWork(postgres_session_factory) as unit_of_work:
        unit_of_work.session.execute(text("select 1"))
