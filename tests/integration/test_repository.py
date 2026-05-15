from typing import TYPE_CHECKING

import pytest

from allocation.adapters.repository import SqlAlchemyRepository
from allocation.domain.model import Batch, Product

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, sessionmaker

pytestmark = pytest.mark.usefixtures("mappers")


def test_get_by_batch_reference(sqlite_session_factory: sessionmaker[Session]) -> None:
    session = sqlite_session_factory()
    repo = SqlAlchemyRepository(session)
    b1 = Batch(reference="b1", stock_keeping_unit="stock_keeping_unit1", quantity=100, estimated_time_of_arrival=None)
    b2 = Batch(reference="b2", stock_keeping_unit="stock_keeping_unit1", quantity=100, estimated_time_of_arrival=None)
    b3 = Batch(reference="b3", stock_keeping_unit="stock_keeping_unit2", quantity=100, estimated_time_of_arrival=None)
    p1 = Product(stock_keeping_unit="stock_keeping_unit1", batches=[b1, b2])
    p2 = Product(stock_keeping_unit="stock_keeping_unit2", batches=[b3])
    repo.add(p1)
    repo.add(p2)
    assert repo.get_by_batch_reference("b2") == p1
    assert repo.get_by_batch_reference("b3") == p2
