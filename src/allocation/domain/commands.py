# pylint: disable=too-few-public-methods
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
    qty: int


@dataclass
class CreateBatch(Command):
    ref: str
    sku: str
    qty: int
    eta: date | None = None


@dataclass
class ChangeBatchQuantity(Command):
    ref: str
    qty: int
