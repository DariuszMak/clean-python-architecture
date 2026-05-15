from dataclasses import dataclass


class Event:
    pass


@dataclass
class Allocated(Event):
    orderid: str
    stock_keeping_unit: str
    quantity: int
    batchreference: str


@dataclass
class Deallocated(Event):
    orderid: str
    stock_keeping_unit: str
    quantity: int


@dataclass
class OutOfStock(Event):
    stock_keeping_unit: str
