from pydantic import BaseModel


class Event(BaseModel):
    pass


class Allocated(Event):
    orderid: str
    sku: str
    qty: int
    batchref: str


class Deallocated(Event):
    orderid: str
    sku: str
    qty: int


class OutOfStock(Event):
    sku: str