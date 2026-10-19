"""Input validation for order replay and generation; errors propagate directly."""
from math import isfinite

from warehouse_api.contracts import Order


def _time(value: float, name: str) -> None:
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError(f"{name}: expected a finite nonnegative time")


def _identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: expected a nonblank string")


def _positive_int(value: int, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name}: expected a positive integer")


def validate_orders(orders: tuple[Order, ...]) -> None:
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
        for item in order.items:
            _identifier(item.sku, f"{order.id}.sku")
            _positive_int(item.quantity, f"{order.id}.{item.sku}.quantity")


def validate_release_time(until_s: float, previous_s: float) -> None:
    _time(until_s, "until_s")
    if until_s < previous_s:
        raise ValueError(f"until_s: time moved backward from {previous_s} to {until_s}")


def validate_generation_parameters(
    seed: int,
    count: int,
    skus: tuple[str, ...],
    release_interval_s: float,
    max_quantity: int,
    due_after_s: float | None,
) -> None:
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
