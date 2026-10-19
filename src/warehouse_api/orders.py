"""Replayable demand only; no inventory, assignment, or runtime writes."""
from random import Random

from warehouse_api._order_validation import (
    validate_generation_parameters,
    validate_orders,
    validate_release_time,
)
from warehouse_api.contracts import Item, Order


class ReplayOrderSource:
    """Implement OrderSource with an inclusive, monotonic release cursor."""

    def __init__(self, orders: tuple[Order, ...] = ()) -> None:
        self.reset(orders)

    def reset(self, orders: tuple[Order, ...]) -> None:
        """Validate all orders before replacing the current replay state."""
        validate_orders(orders)
        normalized = []
        for order in orders:
            quantities: dict[str, int] = {}
            for item in order.items:
                quantities[item.sku] = quantities.get(item.sku, 0) + item.quantity
            items = tuple(Item(sku, quantity) for sku, quantity in sorted(quantities.items()))
            normalized.append(Order(order.id, order.released_at_s, items, order.due_at_s))
        self._orders = tuple(sorted(normalized, key=lambda order: (order.released_at_s, order.id)))
        self._cursor = 0
        self._until_s = 0.0

    def release(self, until_s: float) -> tuple[Order, ...]:
        """Return each due order once; invalid calls leave the cursor intact."""
        validate_release_time(until_s, self._until_s)
        end = self._cursor
        while end < len(self._orders) and self._orders[end].released_at_s <= until_s:
            end += 1
        released = self._orders[self._cursor:end]
        self._cursor = end
        self._until_s = until_s
        return released


def generate_orders(
    *,
    seed: int,
    count: int,
    skus: tuple[str, ...],
    release_interval_s: float = 1.0,
    max_quantity: int = 5,
    due_after_s: float | None = None,
) -> tuple[Order, ...]:
    """Generate demand using a private RNG and explicit experiment parameters.

    Release order i at i * release_interval_s, starting at zero. Choose a
    uniform item count in [1, len(skus)], sample distinct SKUs, then choose
    each quantity uniformly in [1, max_quantity]. IDs are order-0, order-1,
    etc. A due offset of None disables deadlines. Reproducibility requires
    the same parameters and Python version; persist orders for other versions.
    """
    validate_generation_parameters(
        seed, count, skus, release_interval_s, max_quantity, due_after_s,
    )
    rng = Random(seed)
    catalog = sorted(skus)
    orders = []
    for index in range(count):
        chosen = rng.sample(catalog, rng.randint(1, len(catalog)))
        items = tuple(Item(sku, rng.randint(1, max_quantity)) for sku in sorted(chosen))
        release = index * release_interval_s
        due = None if due_after_s is None else release + due_after_s
        orders.append(Order(f"order-{index}", release, items, due))
    return tuple(orders)
