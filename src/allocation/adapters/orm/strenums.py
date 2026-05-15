from enum import StrEnum

class TableName(StrEnum):
    ORDER_LINES = "order_lines"
    PRODUCTS = "products"
    BATCHES = "batches"
    ALLOCATIONS = "allocations"
    ALLOCATIONS_VIEW = "allocations_view"


class ColumnName(StrEnum):
    ID = "id"
    SKU = "sku"
    QTY = "qty"
    ORDERID = "orderid"
    VERSION_NUMBER = "version_number"
    REFERENCE = "reference"
    PURCHASED_QUANTITY = "_purchased_quantity"
    ETA = "eta"
    ORDERLINE_ID = "orderline_id"
    BATCH_ID = "batch_id"
    BATCHREF = "batchref"


class RelationshipName(StrEnum):
    ALLOCATIONS = "_allocations"
    BATCHES = "batches"


class EventName(StrEnum):
    LOAD = "load"
