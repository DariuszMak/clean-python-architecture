from typing import Any

import pytest
import requests
from sqlalchemy.orm import Session, clear_mappers, sessionmaker

from src import config
from src.adapters import notifications
from src.bootstrap import bootstrap
from src.domain.commands import Allocate, CreateBatch
from src.service_layer.unit_of_work import SqlAlchemyUnitOfWork
from tests.random_references import random_stock_keeping_unit


@pytest.fixture
def bus(sqlite_session_factory: sessionmaker[Session]) -> Any:
    yield bootstrap(
        start_orm=True,
        unit_of_work=SqlAlchemyUnitOfWork(sqlite_session_factory),
        notifications=notifications.EmailNotifications(),
        publish=lambda *_: None,
    )
    clear_mappers()


def get_email_from_mailhog(stock_keeping_unit: str) -> dict[str, Any]:
    host, port = map(config.get_email_host_and_port().get, ["host", "http_port"])
    all_emails = requests.get(
        f"http://{host}:{port}/api/v2/messages",
        timeout=5,
    ).json()
    return next(m for m in all_emails["items"] if stock_keeping_unit in str(m))


def test_out_of_stock_email(bus: Any) -> None:
    stock_keeping_unit = random_stock_keeping_unit()
    bus.handle(CreateBatch("batch1", stock_keeping_unit, 9, None))
    bus.handle(Allocate("order1", stock_keeping_unit, 10))
    email = get_email_from_mailhog(stock_keeping_unit)
    assert email["Raw"]["From"] == "allocations@example.com"
    assert email["Raw"]["To"] == ["stock@made.com"]
    assert f"Out of stock for {stock_keeping_unit}" in email["Raw"]["Data"]
