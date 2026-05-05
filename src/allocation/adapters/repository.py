import abc
from typing import Any, Set

from allocation.adapters import orm
from allocation.domain import model


class AbstractRepository(abc.ABC):
    def __init__(self) -> None:
        self.seen: Set[model.Product] = set()

    def add(self, product: model.Product) -> None:
        self._add(product)
        self.seen.add(product)

    def get(self, sku: str) -> model.Product:
        product = self._get(sku)
        if product:
            self.seen.add(product)
        return product

    def get_by_batchref(self, batchref: str) -> model.Product:
        product = self._get_by_batchref(batchref)
        if product:
            self.seen.add(product)
        return product

    @abc.abstractmethod
    def _add(self, product: model.Product) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, sku: str) -> model.Product:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_by_batchref(self, batchref: str) -> model.Product:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session: Any) -> None:
        super().__init__()
        self.session = session

    def _add(self, product: model.Product) -> None:
        self.session.add(product)

    def _get(self, sku: str) -> model.Product:
        return self.session.query(model.Product).filter_by(sku=sku).first()

    def _get_by_batchref(self, batchref: str) -> model.Product:
        return (
            self.session
            .query(model.Product)
            .join(model.Batch)
            .filter(
                orm.batches.c.reference == batchref,
            )
            .first()
        )
