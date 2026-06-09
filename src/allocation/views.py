from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from service_layer.unit_of_work import SqlAlchemyUnitOfWork


def allocations(order_id: str, unit_of_work: SqlAlchemyUnitOfWork) -> list[dict[str, str]]:
    with unit_of_work:
        results = list(
            unit_of_work.session.execute(
                text("SELECT stock_keeping_unit, batch_reference FROM allocations_view WHERE order_id = :order_id"),
                {"order_id": order_id},
            )
        )
    return [dict(r._mapping) for r in results]
