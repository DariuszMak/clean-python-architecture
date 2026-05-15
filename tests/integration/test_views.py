from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from unittest import mock

import pytest
from sqlalchemy.orm import Session, clear_mappers, sessionmaker

from allocation.bootstrap import bootstrap
from allocation.domain.commands import Allocate, ChangeBatchQuantity, CreateBatch
from allocation.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from allocation.views import allocations

if TYPE_CHECKING:
    from collections.abc import Iterator

    from allocation.service_layer.messagebus import MessageBus

today = datetime.now(tz=UTC).date()


@pytest.fixture
def sqlite_bus(sqlite_session_factory: sessionmaker[Session]) -> Iterator[MessageBus]:
    yield bootstrap(
        start_orm=True,
        uow=SqlAlchemyUnitOfWork(sqlite_session_factory),
        notifications=mock.Mock(),
        publish=lambda *_: None,
    )
    clear_mappers()


def test_allocations_view(sqlite_bus: MessageBus) -> None:
    sqlite_bus.handle(CreateBatch("stock_keeping_unit1batch", "stock_keeping_unit1", 50, None))
    sqlite_bus.handle(CreateBatch("stock_keeping_unit2batch", "stock_keeping_unit2", 50, today))
    sqlite_bus.handle(Allocate("order1", "stock_keeping_unit1", 20))
    sqlite_bus.handle(Allocate("order1", "stock_keeping_unit2", 20))

    sqlite_bus.handle(CreateBatch("stock_keeping_unit1batch-later", "stock_keeping_unit1", 50, today))
    sqlite_bus.handle(Allocate("otherorder", "stock_keeping_unit1", 30))
    sqlite_bus.handle(Allocate("otherorder", "stock_keeping_unit2", 10))

    assert allocations(
        "order1",
        cast("SqlAlchemyUnitOfWork", sqlite_bus.uow),
    ) == [
        {"stock_keeping_unit": "stock_keeping_unit1", "batchreference": "stock_keeping_unit1batch"},
        {"stock_keeping_unit": "stock_keeping_unit2", "batchreference": "stock_keeping_unit2batch"},
    ]


def test_deallocation(sqlite_bus: MessageBus) -> None:
    sqlite_bus.handle(CreateBatch("b1", "stock_keeping_unit1", 50, None))
    sqlite_bus.handle(CreateBatch("b2", "stock_keeping_unit1", 50, today))
    sqlite_bus.handle(Allocate("o1", "stock_keeping_unit1", 40))
    sqlite_bus.handle(ChangeBatchQuantity("b1", 10))

    assert allocations(
        "o1",
        cast("SqlAlchemyUnitOfWork", sqlite_bus.uow),
    ) == [
        {"stock_keeping_unit": "stock_keeping_unit1", "batchreference": "b2"},
    ]
