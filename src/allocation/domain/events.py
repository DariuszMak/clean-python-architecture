from dataclasses import dataclass


class Event:
    pass


@dataclass
class Allocated(Event):
    order_id: str
    stock_keeping_unit: str
    quantity: int
    batch_reference: str


@dataclass
class Deallocated(Event):
    order_id: str
    stock_keeping_unit: str
    quantity: int


@dataclass
class OutOfStock(Event):
    stock_keeping_unit: str
