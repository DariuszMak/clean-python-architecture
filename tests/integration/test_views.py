from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from sqlalchemy.orm import Session, clear_mappers, sessionmaker

from allocation import bootstrap, views
from allocation.domain import commands
from allocation.service_layer import unit_of_work

if TYPE_CHECKING:
    from allocation.service_layer.messagebus import MessageBus

today = datetime.now(tz=UTC).date()


@pytest.fixture
def sqlite_bus(sqlite_session_factory: sessionmaker[Session]) -> MessageBus:
    yield bootstrap(
        start_orm=True,
        uow=unit_of_work.SqlAlchemyUnitOfWork(sqlite_session_factory),
        notifications=mock.Mock(),
        publish=lambda *_: None,
    )
    clear_mappers()


def test_allocations_view(sqlite_bus: MessageBus) -> None:
    sqlite_bus.handle(commands.CreateBatch("sku1batch", "sku1", 50, None))
    sqlite_bus.handle(commands.CreateBatch("sku2batch", "sku2", 50, today))
    sqlite_bus.handle(commands.Allocate("order1", "sku1", 20))
    sqlite_bus.handle(commands.Allocate("order1", "sku2", 20))

    sqlite_bus.handle(commands.CreateBatch("sku1batch-later", "sku1", 50, today))
    sqlite_bus.handle(commands.Allocate("otherorder", "sku1", 30))
    sqlite_bus.handle(commands.Allocate("otherorder", "sku2", 10))

    assert views.allocations("order1", sqlite_bus.uow) == [
        {"sku": "sku1", "batchref": "sku1batch"},
        {"sku": "sku2", "batchref": "sku2batch"},
    ]


def test_deallocation(sqlite_bus: MessageBus) -> None:
    sqlite_bus.handle(commands.CreateBatch("b1", "sku1", 50, None))
    sqlite_bus.handle(commands.CreateBatch("b2", "sku1", 50, today))
    sqlite_bus.handle(commands.Allocate("o1", "sku1", 40))
    sqlite_bus.handle(commands.ChangeBatchQuantity("b1", 10))

    assert views.allocations("o1", sqlite_bus.uow) == [
        {"sku": "sku1", "batchref": "b2"},
    ]
