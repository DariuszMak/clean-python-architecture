from typing import Any

import pytest

from src.adapters.repository import AbstractRepository
from src.service_layer.unit_of_work import AbstractUnitOfWork


class BareRepository(AbstractRepository):
    def _add(self, product: Any) -> Any:
        raise NotImplementedError

    def _get(self, stock_keeping_unit: str) -> Any:
        raise NotImplementedError

    def _get_by_batch_reference(self, batch_reference: str) -> Any:
        raise NotImplementedError


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


class BareUnitOfWork(AbstractUnitOfWork):
    def _commit(self) -> None:
        raise NotImplementedError

    def rollback(self) -> None:
        raise NotImplementedError


def test_abstract_unit_of_work_commit_raises() -> None:
    unit_of_work = BareUnitOfWork()
    with pytest.raises(NotImplementedError):
        unit_of_work._commit()


def test_abstract_unit_of_work_rollback_raises() -> None:
    unit_of_work = BareUnitOfWork()
    with pytest.raises(NotImplementedError):
        unit_of_work.rollback()
