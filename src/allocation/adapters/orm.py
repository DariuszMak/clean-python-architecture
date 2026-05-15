import logging
from typing import Any

from sqlalchemy import Column, Date, ForeignKey, Integer, MetaData, String, Table, event
from sqlalchemy.orm import registry, relationship

from allocation.domain.model import Batch, OrderLine, Product

logger = logging.getLogger(__name__)

metadata = MetaData()
mapper_registry = registry()

order_lines = Table(
    "order_lines",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("stock_keeping_unit", String(255)),
    Column("quantity", Integer, nullable=False),
    Column("order_id", String(255)),
)

products = Table(
    "products",
    metadata,
    Column("stock_keeping_unit", String(255), primary_key=True),
    Column("version_number", Integer, nullable=False, server_default="0"),
)

batches = Table(
    "batches",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("reference", String(255)),
    Column("stock_keeping_unit", ForeignKey("products.stock_keeping_unit")),
    Column("_purchased_quantity", Integer, nullable=False),
    Column("estimated_time_of_arrival", Date, nullable=True),
)

allocations = Table(
    "allocations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("orderline__id", ForeignKey("order_lines.id")),
    Column("batch__id", ForeignKey("batches.id")),
)

allocations_view = Table(
    "allocations_view",
    metadata,
    Column("order_id", String(255)),
    Column("stock_keeping_unit", String(255)),
    Column("batch_reference", String(255)),
)


def start_mappers() -> None:
    if mapper_registry.mappers:
        return
    logger.info("Starting mappers")
    lines_mapper = mapper_registry.map_imperatively(OrderLine, order_lines)
    batches_mapper = mapper_registry.map_imperatively(
        Batch,
        batches,
        properties={
            "_allocations": relationship(
                lines_mapper,
                secondary=allocations,
                collection_class=set,
            )
        },
    )
    mapper_registry.map_imperatively(
        Product,
        products,
        properties={"batches": relationship(batches_mapper)},
    )


@event.listens_for(Product, "load")
def receive_load(product: Product, _: Any) -> None:
    product.events = []
