from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import events

if TYPE_CHECKING:
    from datetime import date


class Product:
    def __init__(self, stock_keeping_unit: str, batches: list[Batch], version_number: int = 0) -> None:
        self.stock_keeping_unit = stock_keeping_unit
        self.batches = batches
        self.version_number = version_number
        self.events: list[object] = []

    def allocate(self, line: OrderLine) -> str | None:
        try:
            batch = next(b for b in sorted(self.batches) if b.can_allocate(line))
        except StopIteration:
            self.events.append(events.OutOfStock(line.stock_keeping_unit))
            return None
        else:
            batch.allocate(line)
            self.version_number += 1
            self.events.append(
                events.Allocated(
                    order_id=line.order_id,
                    stock_keeping_unit=line.stock_keeping_unit,
                    quantity=line.quantity,
                    batch_reference=batch.reference,
                )
            )
            return batch.reference

    def change_batch_quantity(self, reference: str, quantity: int) -> None:
        batch = next(b for b in self.batches if b.reference == reference)
        batch._purchased_quantity = quantity
        while batch.available_quantity < 0:
            line = batch.deallocate_one()
            self.events.append(events.Deallocated(line.order_id, line.stock_keeping_unit, line.quantity))


@dataclass(unsafe_hash=True)
class OrderLine:
    order_id: str
    stock_keeping_unit: str
    quantity: int


class Batch:
    def __init__(
        self, reference: str, stock_keeping_unit: str, quantity: int, estimated_time_of_arrival: date | None
    ) -> None:
        self.reference = reference
        self.stock_keeping_unit = stock_keeping_unit
        self.estimated_time_of_arrival = estimated_time_of_arrival
        self._purchased_quantity = quantity
        self._allocations: set[OrderLine] = set()

    def __repr__(self) -> str:
        return f"<Batch {self.reference}>"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Batch):
            return False
        return other.reference == self.reference

    def __hash__(self) -> int:
        return hash(self.reference)

    def __gt__(self, other: Batch) -> bool:
        if self.estimated_time_of_arrival is None:
            return False
        if other.estimated_time_of_arrival is None:
            return True
        return self.estimated_time_of_arrival > other.estimated_time_of_arrival

    def allocate(self, line: OrderLine) -> None:
        if self.can_allocate(line):
            self._allocations.add(line)

    def deallocate_one(self) -> OrderLine:
        return self._allocations.pop()

    @property
    def allocated_quantity(self) -> int:
        return sum(line.quantity for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_quantity - self.allocated_quantity

    def can_allocate(self, line: OrderLine) -> bool:
        return self.stock_keeping_unit == line.stock_keeping_unit and self.available_quantity >= line.quantity
