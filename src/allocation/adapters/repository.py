import abc
from typing import TYPE_CHECKING

from src.allocation.adapters.orm.orm import batches
from allocation.domain.model import Batch, Product

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class AbstractRepository(abc.ABC):
    def __init__(self) -> None:
        self.seen: set[Product] = set()

    def add(self, product: Product) -> None:
        self._add(product)
        self.seen.add(product)

    def get(self, sku: str) -> Product | None:
        product = self._get(sku)
        if product:
            self.seen.add(product)
        return product

    def get_by_batchref(self, batchref: str) -> Product | None:
        product = self._get_by_batchref(batchref)
        if product:
            self.seen.add(product)
        return product

    @abc.abstractmethod
    def _add(self, product: Product) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, sku: str) -> Product | None:
        raise NotImplementedError

    @abc.abstractmethod
    def _get_by_batchref(self, batchref: str) -> Product | None:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session

    def _add(self, product: Product) -> None:
        self.session.add(product)

    def _get(self, sku: str) -> Product | None:
        return self.session.query(Product).filter_by(sku=sku).first()

    def _get_by_batchref(self, batchref: str) -> Product | None:
        return self.session.query(Product).join(Batch).filter(batches.c.reference == batchref).first()
