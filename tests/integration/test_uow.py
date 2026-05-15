import threading
import time
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import text

from allocation.domain.model import OrderLine
from allocation.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from tests.random_references import random_batchreference, random_orderid, random_stock_keeping_unit

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, sessionmaker

pytestmark = pytest.mark.usefixtures("mappers")


def insert_batch(
    session: Session,
    referenceerence: str,
    stock_keeping_unit: str,
    quantity: int,
    eta: Any,
    product_version: int = 1,
) -> None:
    session.execute(
        text("INSERT INTO products (stock_keeping_unit, version_number) VALUES (:stock_keeping_unit, :version)"),
        {"stock_keeping_unit": stock_keeping_unit, "version": product_version},
    )
    session.execute(
        text(
            "INSERT INTO batches (referenceerence, stock_keeping_unit, _purchased_quantity, eta) VALUES (:referenceerence, :stock_keeping_unit, :quantity, :eta)"
        ),
        {"referenceerence": referenceerence, "stock_keeping_unit": stock_keeping_unit, "quantity": quantity, "eta": eta},
    )


def get_allocated_batch_reference(session: Session, orderid: str, stock_keeping_unit: str) -> str:
    [[orderlineid]] = session.execute(
        text("SELECT id FROM order_lines WHERE orderid=:orderid AND stock_keeping_unit=:stock_keeping_unit"),
        {"orderid": orderid, "stock_keeping_unit": stock_keeping_unit},
    )
    [[batchreference]] = session.execute(
        text(
            "SELECT b.referenceerence FROM allocations JOIN batches AS b ON batch_id = b.id WHERE orderline_id=:orderlineid"
        ),
        {"orderlineid": orderlineid},
    )
    return str(batchreference)


def test_uow_can_retrieve_a_batch_and_allocate_to_it(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    session = sqlite_session_factory()
    insert_batch(session, "batch1", "HIPSTER-WORKBENCH", 100, None)
    session.commit()

    uow = SqlAlchemyUnitOfWork(sqlite_session_factory)
    with uow:
        product = uow.products.get(stock_keeping_unit="HIPSTER-WORKBENCH")
        line = OrderLine("o1", "HIPSTER-WORKBENCH", 10)
        product.allocate(line)
        uow.commit()

    batchreference = get_allocated_batch_reference(session, "o1", "HIPSTER-WORKBENCH")
    assert batchreference == "batch1"


def test_rolls_back_uncommitted_work_by_default(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    uow = SqlAlchemyUnitOfWork(sqlite_session_factory)
    with uow:
        insert_batch(uow.session, "batch1", "MEDIUM-PLINTH", 100, None)

    new_session = sqlite_session_factory()
    rows = list(new_session.execute(text('SELECT * FROM "batches"')))
    assert rows == []


def test_rolls_back_on_error(
    sqlite_session_factory: sessionmaker[Session],
) -> None:
    class MyError(Exception):
        pass

    uow = SqlAlchemyUnitOfWork(sqlite_session_factory)

    with uow:
        insert_batch(uow.session, "batch1", "LARGE-FORK", 100, None)
        with pytest.raises(MyError):
            raise MyError

    new_session = sqlite_session_factory()
    rows = list(new_session.execute(text('SELECT * FROM "batches"')))

    assert rows == []


def try_to_allocate(
    orderid: str,
    stock_keeping_unit: str,
    exceptions: list[Exception],
    session_factory: sessionmaker[Session],
) -> None:
    line = OrderLine(orderid, stock_keeping_unit, 10)
    try:
        with SqlAlchemyUnitOfWork(session_factory) as uow:
            product = uow.products.get(stock_keeping_unit=stock_keeping_unit)
            product.allocate(line)
            time.sleep(0.2)
            uow.commit()
    except Exception as e:
        exceptions.append(e)


def test_concurrent_updates_to_version_are_not_allowed(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    stock_keeping_unit, batch = random_stock_keeping_unit(), random_batchreference()
    session = postgres_session_factory()
    insert_batch(session, batch, stock_keeping_unit, 100, eta=None, product_version=1)
    session.commit()

    order1, order2 = random_orderid("1"), random_orderid("2")
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
                "SELECT orderid FROM allocations"
                " JOIN batches ON allocations.batch_id = batches.id"
                " JOIN order_lines ON allocations.orderline_id = order_lines.id"
                " WHERE order_lines.stock_keeping_unit=:stock_keeping_unit"
            ),
            {"stock_keeping_unit": stock_keeping_unit},
        )
    )
    assert len(orders) == 1
    with SqlAlchemyUnitOfWork(postgres_session_factory) as uow:
        uow.session.execute(text("select 1"))
