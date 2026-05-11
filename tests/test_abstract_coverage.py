"""Tests targeting uncovered abstract method bodies in repository.py and unit_of_work.py."""

import pytest

from allocation.adapters.repository import AbstractRepository
from allocation.service_layer.unit_of_work import AbstractUnitOfWork

# ── repository.py lines 33, 37, 41 ──────────────────────────────────────────


class BareRepository(AbstractRepository):
    """Subclass that calls super() on each abstract method to hit the raise lines."""

    def _add(self, product):  # type: ignore[override]
        return super()._add(product)

    def _get(self, sku):  # type: ignore[override]
        return super()._get(sku)

    def _get_by_batchref(self, batchref):  # type: ignore[override]
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


# ── unit_of_work.py lines 38, 42 ────────────────────────────────────────────


class BareUnitOfWork(AbstractUnitOfWork):
    """Subclass that calls super() on each abstract method to hit the raise lines."""

    def _commit(self):  # type: ignore[override]
        return super()._commit()

    def rollback(self):  # type: ignore[override]
        return super().rollback()


def test_abstract_uow_commit_raises() -> None:
    uow = BareUnitOfWork()
    with pytest.raises(NotImplementedError):
        uow._commit()


def test_abstract_uow_rollback_raises() -> None:
    uow = BareUnitOfWork()
    with pytest.raises(NotImplementedError):
        uow.rollback()
