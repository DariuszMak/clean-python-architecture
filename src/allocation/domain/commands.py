from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Command(BaseModel):
    pass


class Allocate(Command):
    orderid: str
    sku: str
    qty: int


class CreateBatch(Command):
    ref: str
    sku: str
    qty: int
    eta: date | None = None


class ChangeBatchQuantity(Command):
    ref: str
    qty: int