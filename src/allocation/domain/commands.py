from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date


class Command:
    pass


@dataclass
class Allocate(Command):
    orderid: str
    stock_keeping_unit: str
    quantity: int


@dataclass
class CreateBatch(Command):
    reference: str
    stock_keeping_unit: str
    quantity: int
    estimated_time_of_arrival: date | None = None


@dataclass
class ChangeBatchQuantity(Command):
    reference: str
    quantity: int
