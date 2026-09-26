"""A tiny shopping cart — the sandbox for trying /jira-loop.

It is deliberately small and deliberately imperfect: see ../specs/ for
the bug, story and task you can hand to the pipeline.
"""
from dataclasses import dataclass

BULK_DISCOUNT_THRESHOLD = 100.0
BULK_DISCOUNT_PERCENT = 10.0


@dataclass
class Item:
    sku: str
    name: str
    unit_price: float
    qty: int = 1

    @property
    def line_total(self) -> float:
        return self.unit_price * self.qty


class Cart:
    def __init__(self) -> None:
        self.items: dict[str, Item] = {}

    def add(self, sku: str, name: str, unit_price: float, qty: int = 1) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        if unit_price < 0:
            raise ValueError("unit_price must not be negative")
        if sku in self.items:
            self.items[sku].qty += qty
        else:
            self.items[sku] = Item(sku, name, unit_price, qty)

    def remove(self, sku: str) -> None:
        del self.items[sku]

    def item_count(self) -> int:
        return sum(item.qty for item in self.items.values())

    def subtotal(self) -> float:
        return sum(item.line_total for item in self.items.values())

    def discount(self) -> float:
        subtotal = self.subtotal()
        if subtotal > BULK_DISCOUNT_THRESHOLD:
            return subtotal * BULK_DISCOUNT_PERCENT / 100
        return 0.0

    def total(self) -> float:
        return round(self.subtotal() - self.discount(), 2)
