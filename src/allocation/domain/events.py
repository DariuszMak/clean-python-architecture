from dataclasses import dataclass


class Event:
    pass


@dataclass
class Allocated(Event):
    orderid: str
    sku: str
    quantity: int
    batchreference: str


@dataclass
class Deallocated(Event):
    orderid: str
    sku: str
    quantity: int


@dataclass
class OutOfStock(Event):
    sku: str
