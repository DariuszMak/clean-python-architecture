from typing import Any

import pytest

from allocation.adapters.repository import AbstractRepository
from allocation.service_layer.unit_of_work import AbstractUnitOfWork


class BareRepository(AbstractRepository):  # type: ignore[misc]
    def _add(self, product: Any) -> Any:
        super()._add(product)

    def _get(self, sku: str) -> Any:
        return super()._get(sku)

    def _get_by_batchref(self, batchref: str) -> Any:
        return super()._get_by_batchref(batchref)


def test_abstract_repository_add_raises() -> None:
    repo = BareRepository()
    with pytest.raises(NotImplementedError):
        repo._add(object())


def test_abstract_repository_get_raises() -> None:
    repo = BareRepository()
    with pytest.raises(NotImplementedError):
        repo._get("any-sku")


def test_abstract_repository_get_by_batchref_raises() -> None:
    repo = BareRepository()
    with pytest.raises(NotImplementedError):
        repo._get_by_batchref("any-ref")


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
