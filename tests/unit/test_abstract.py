from typing import Any

import pytest

from src.adapters.repository import AbstractRepository
from src.service_layer.unit_of_work import AbstractUnitOfWork


class BareRepository(AbstractRepository):  # type: ignore[misc]
    def _add(self, product: Any) -> Any:
        super()._add(product)

    def _get(self, stock_keeping_unit: str) -> Any:
        return super()._get(stock_keeping_unit)

    def _get_by_batch_reference(self, batch_reference: str) -> Any:
        return super()._get_by_batch_reference(batch_reference)


def test_abstract_repository_add_raises() -> None:
    repo = BareRepository()
    with pytest.raises(NotImplementedError):
        repo._add(object())


def test_abstract_repository_get_raises() -> None:
    repo = BareRepository()
    with pytest.raises(NotImplementedError):
        repo._get("any-stock_keeping_unit")


def test_abstract_repository_get_by_batch_reference_raises() -> None:
    repo = BareRepository()
    with pytest.raises(NotImplementedError):
        repo._get_by_batch_reference("any-reference")


class BareUnitOfWork(AbstractUnitOfWork):  # type: ignore[misc]
    def _commit(self) -> None:
        super()._commit()

    def rollback(self) -> None:
        super().rollback()


def test_abstract_unit_of_work_commit_raises() -> None:
    unit_of_work = BareUnitOfWork()
    with pytest.raises(NotImplementedError):
        unit_of_work._commit()


def test_abstract_unit_of_work_rollback_raises() -> None:
    unit_of_work = BareUnitOfWork()
    with pytest.raises(NotImplementedError):
        unit_of_work.rollback()
