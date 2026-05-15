from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from allocation.service_layer.unit_of_work import SqlAlchemyUnitOfWork


def allocations(orderid: str, unit_of_work: SqlAlchemyUnitOfWork) -> list[dict[str, str]]:
    with unit_of_work:
        results = list(
            unit_of_work.session.execute(
                text("SELECT stock_keeping_unit, batchreference FROM allocations_view WHERE orderid = :orderid"),
                {"orderid": orderid},
            )
        )
    return [dict(r._mapping) for r in results]
