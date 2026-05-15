from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date


class Command:
    pass


@dataclass
class Allocate(Command):
    orderid: str
    sku: str
    quantity: int


@dataclass
class CreateBatch(Command):
    referenceerence: str
    sku: str
    quantity: int
    eta: date | None = None


@dataclass
class ChangeBatchQuantity(Command):
    referenceerence: str
    quantity: int
