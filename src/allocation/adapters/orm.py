import logging
from typing import Any

from sqlalchemy import Column, Date, ForeignKey, Integer, MetaData, String, Table, event
from sqlalchemy.orm import registry, relationship

from allocation.domain.model import Batch, OrderLine, Product
from src.allocation.helpers.strenums import TableName

logger = logging.getLogger(__name__)

metadata = MetaData()
mapper_registry = registry()

order_lines = Table(
    TableName.ORDER_LINES.value,
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
    Column("orderid", String(255)),
)

products = Table(
    TableName.PRODUCTS.value,
    metadata,
    Column("sku", String(255), primary_key=True),
    Column("version_number", Integer, nullable=False, server_default="0"),
)

batches = Table(
    TableName.BATCHES.value,
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("reference", String(255)),
    Column("sku", ForeignKey("products.sku")),
    Column("_purchased_quantity", Integer, nullable=False),
    Column("eta", Date, nullable=True),
)

allocations = Table(
    TableName.ALLOCATIONS.value,
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("orderline_id", ForeignKey("order_lines.id")),
    Column("batch_id", ForeignKey("batches.id")),
)

allocations_view = Table(
    TableName.ALLOCATIONS_VIEW.value,
    metadata,
    Column("orderid", String(255)),
    Column("sku", String(255)),
    Column("batchref", String(255)),
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
