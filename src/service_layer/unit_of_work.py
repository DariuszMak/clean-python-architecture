from __future__ import annotations

import abc
import importlib
from typing import TYPE_CHECKING, Any, Self

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from adapters.repository import SqlAlchemyRepository

if TYPE_CHECKING:
    from collections.abc import Iterator

config = importlib.import_module("config")
repository = importlib.import_module("adapters.repository")


class AbstractUnitOfWork(abc.ABC):
    products: Any

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any) -> None:
        self.rollback()

    def commit(self) -> None:
        self._commit()

    def collect_new_events(self) -> Iterator[Any]:
        for product in self.products.seen:
            while product.events:
                yield product.events.pop(0)

    @abc.abstractmethod
    def _commit(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError


DEFAULT_SESSION_FACTORY: sessionmaker[Session] = sessionmaker(
    bind=create_engine(
        config.get_postgres_uri(),
        isolation_level="REPEATABLE READ",
    )
)


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    session: Session
    session_factory: sessionmaker[Session]

    def __init__(self, session_factory: sessionmaker[Session] = DEFAULT_SESSION_FACTORY) -> None:
        self.session_factory = session_factory

    def __enter__(self) -> Self:
        self.session = self.session_factory()
        self.products = SqlAlchemyRepository(self.session)
        return super().__enter__()

    def __exit__(self, *args: Any) -> None:
        super().__exit__(*args)
        self.session.close()

    def _commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
