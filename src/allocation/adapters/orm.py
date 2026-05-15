import logging
from enum import StrEnum
from typing import Any

from sqlalchemy import Column, Date, ForeignKey, Integer, MetaData, String, Table, event
from sqlalchemy.orm import registry, relationship

from allocation.domain.model import Batch, OrderLine, Product
from src.allocation.helpers.strenums import ColumnName, EventName, RelationshipName, TableName

logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)

metadata = MetaData()
mapper_registry = registry()

order_lines = Table(
    TableName.ORDER_LINES,
    metadata,
    Column(ColumnName.ID, Integer, primary_key=True, autoincrement=True),
    Column(ColumnName.SKU, String(255)),
    Column(ColumnName.QTY, Integer, nullable=False),
    Column(ColumnName.ORDERID, String(255)),
)

products = Table(
    TableName.PRODUCTS,
    metadata,
    Column(ColumnName.SKU, String(255), primary_key=True),
    Column(ColumnName.VERSION_NUMBER, Integer, nullable=False, server_default="0"),
)

batches = Table(
    TableName.BATCHES,
    metadata,
    Column(ColumnName.ID, Integer, primary_key=True, autoincrement=True),
    Column(ColumnName.REFERENCE, String(255)),
    Column(
        ColumnName.SKU,
        ForeignKey(f"{TableName.PRODUCTS}.{ColumnName.SKU}"),
    ),
    Column(ColumnName.PURCHASED_QUANTITY, Integer, nullable=False),
    Column(ColumnName.ETA, Date, nullable=True),
)

allocations = Table(
    TableName.ALLOCATIONS,
    metadata,
    Column(ColumnName.ID, Integer, primary_key=True, autoincrement=True),
    Column(
        ColumnName.ORDERLINE_ID,
        ForeignKey(f"{TableName.ORDER_LINES}.{ColumnName.ID}"),
    ),
    Column(
        ColumnName.BATCH_ID,
        ForeignKey(f"{TableName.BATCHES}.{ColumnName.ID}"),
    ),
)

allocations_view = Table(
    TableName.ALLOCATIONS_VIEW,
    metadata,
    Column(ColumnName.ORDERID, String(255)),
    Column(ColumnName.SKU, String(255)),
    Column(ColumnName.BATCHREF, String(255)),
)


def start_mappers() -> None:
    if mapper_registry.mappers:
        return

    logger.info("Starting mappers")

    lines_mapper = mapper_registry.map_imperatively(
        OrderLine,
        order_lines,
    )

    batches_mapper = mapper_registry.map_imperatively(
        Batch,
        batches,
        properties={
            RelationshipName.ALLOCATIONS: relationship(
                lines_mapper,
                secondary=allocations,
                collection_class=set,
            )
        },
    )

    mapper_registry.map_imperatively(
        Product,
        products,
        properties={
            RelationshipName.BATCHES: relationship(batches_mapper),
        },
    )


@event.listens_for(Product, EventName.LOAD)
def receive_load(product: Product, _: Any) -> None:
    product.events = []
