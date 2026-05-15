from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from allocation.service_layer.unit_of_work import SqlAlchemyUnitOfWork


def allocations(orderid: str, uow: SqlAlchemyUnitOfWork) -> list[dict[str, str]]:
    with uow:
        results = list(
            uow.session.execute(
                text("SELECT sku, batchreference FROM allocations_view WHERE orderid = :orderid"),
                {"orderid": orderid},
            )
        )
    return [dict(r._mapping) for r in results]
