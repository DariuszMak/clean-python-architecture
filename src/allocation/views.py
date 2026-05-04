from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from allocation.service_layer import unit_of_work


def allocations(orderid: str, uow: unit_of_work.SqlAlchemyUnitOfWork):
    with uow:
        results = list(
            uow.session.execute(
                text("SELECT sku, batchref FROM allocations_view WHERE orderid = :orderid"),
                {"orderid": orderid},
            )
        )
    return [dict(r._mapping) for r in results]
