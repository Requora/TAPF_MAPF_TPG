"""Replayable demand only; no inventory, assignment, or runtime writes."""
from math import isfinite
from random import Random

from warehouse_api.contracts import Item, Order


def _time(value: float, name: str) -> None:
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError(f"{name}: expected a finite nonnegative time")


def _identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: expected a nonblank string")


def _positive_int(value: int, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name}: expected a positive integer")


class ReplayOrderSource:
    """Implement OrderSource with an inclusive, monotonic release cursor."""

    def __init__(self, orders: tuple[Order, ...] = ()) -> None:
        self.reset(orders)

    def reset(self, orders: tuple[Order, ...]) -> None:
        """Validate all orders before replacing the current replay state."""
        normalized = []
        seen = set()
        for order in orders:
            _identifier(order.id, "order.id")
            if order.id in seen:
                raise ValueError(f"Duplicate order ID: {order.id}")
            seen.add(order.id)
            _time(order.released_at_s, f"{order.id}.released_at_s")
            if order.due_at_s is not None:
                _time(order.due_at_s, f"{order.id}.due_at_s")
            if not order.items:
                raise ValueError(f"{order.id}.items: expected nonempty demand")
            quantities: dict[str, int] = {}
            for item in order.items:
                _identifier(item.sku, f"{order.id}.sku")
                _positive_int(item.quantity, f"{order.id}.{item.sku}.quantity")
                quantities[item.sku] = quantities.get(item.sku, 0) + item.quantity
            items = tuple(Item(sku, quantity) for sku, quantity in sorted(quantities.items()))
            normalized.append(Order(order.id, order.released_at_s, items, order.due_at_s))
        self._orders = tuple(sorted(normalized, key=lambda order: (order.released_at_s, order.id)))
        self._cursor = 0
        self._until_s = 0.0

    def release(self, until_s: float) -> tuple[Order, ...]:
        """Return each due order once; invalid calls leave the cursor intact."""
        _time(until_s, "until_s")
        if until_s < self._until_s:
            raise ValueError(f"until_s: time moved backward from {self._until_s} to {until_s}")
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
    if type(seed) is not int:
        raise ValueError("seed: expected an integer")
    if type(count) is not int or count < 0:
        raise ValueError("count: expected a nonnegative integer")
    if not isinstance(skus, tuple) or not skus:
        raise ValueError("skus: expected a nonempty tuple")
    for sku in skus:
        _identifier(sku, "sku")
    if len(set(skus)) != len(skus):
        raise ValueError("skus: duplicate SKU")
    _time(release_interval_s, "release_interval_s")
    _positive_int(max_quantity, "max_quantity")
    if due_after_s is not None:
        _time(due_after_s, "due_after_s")
    last_release = max(0, count - 1) * release_interval_s
    _time(last_release, "last release")
    if due_after_s is not None:
        _time(last_release + due_after_s, "last due time")
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
