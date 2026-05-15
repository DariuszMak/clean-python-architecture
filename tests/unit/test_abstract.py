from typing import Any

import pytest

from allocation.adapters.repository import AbstractRepository
from allocation.service_layer.unit_of_work import AbstractUnitOfWork


class BareRepository(AbstractRepository):  # type: ignore[misc]
    def _add(self, product: Any) -> Any:
        super()._add(product)

    def _get(self, stock_keeping_unit: str) -> Any:
        return super()._get(stock_keeping_unit)

    def _get_by_batchreference(self, batchreference: str) -> Any:
        return super()._get_by_batchreference(batchreference)


def test_abstract_repository_add_raises() -> None:
    repo = BareRepository()
    with pytest.raises(NotImplementedError):
        repo._add(object())


def test_abstract_repository_get_raises() -> None:
    repo = BareRepository()
    with pytest.raises(NotImplementedError):
        repo._get("any-stock_keeping_unit")


def test_abstract_repository_get_by_batchreference_raises() -> None:
    repo = BareRepository()
    with pytest.raises(NotImplementedError):
        repo._get_by_batchreference("any-referenceerence")


class BareUnitOfWork(AbstractUnitOfWork):  # type: ignore[misc]
    def _commit(self) -> None:
        super()._commit()

    def rollback(self) -> None:
        super().rollback()


def test_abstract_uow_commit_raises() -> None:
    uow = BareUnitOfWork()
    with pytest.raises(NotImplementedError):
        uow._commit()


def test_abstract_uow_rollback_raises() -> None:
    uow = BareUnitOfWork()
    with pytest.raises(NotImplementedError):
        uow.rollback()
