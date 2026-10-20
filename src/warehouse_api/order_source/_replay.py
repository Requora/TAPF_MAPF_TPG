"""Replayable demand only; no inventory, assignment, or runtime writes."""
from random import Random

from ._validation import (
    validate_generation_parameters,
    validate_orders,
    validate_release_time,
)
from warehouse_api.contracts import Item, Order


# 中文: 按仿真时间一次性发布订单, 用可重置游标支持复现实验, 不承担库存预留或机器人分配.
# English: Release each order once by simulation time with a resettable cursor so experiments are
# reproducible without mixing demand release and allocation.
class ReplayOrderSource:
    """Implement OrderSource with an inclusive, monotonic release cursor."""

    # 中文: 通过统一 reset 路径建立初始订单序列, 让构造和重放采用相同校验及归一化规则.
    # English: Initialize through reset so construction and replay use the same validation and
    # normalization rules.
    def __init__(self, orders: tuple[Order, ...] = ()) -> None:
        self.reset(orders)

    # 中文: 先校验再合并 SKU并排序订单, 全部成功后重置游标, 避免非法新序列破坏旧重放状态.
    # English: Validate, merge repeated SKUs and sort orders before resetting the cursor so an
    # invalid replacement cannot destroy the old replay state.
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
        # 中文: 排序键用发布时间和 ID 消除同刻歧义, 保证订单重放顺序稳定.
        # English: Order by release time and ID so simultaneous releases replay deterministically.
        self._orders = tuple(sorted(normalized, key=lambda order: (order.released_at_s, order.id)))
        self._cursor = 0
        self._until_s = 0.0

    # 中文: 返回截止时刻首次到期的订单并推进游标, 使重复调用不重复发布, 且非法时间不改变已发布进度.
    # English: Return newly due orders and advance the cursor so repeated calls do not duplicate
    # demand and invalid times preserve release progress.
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


# 中文: 用私有随机数发生器生成带种子的订单, 隔离全局随机状态, 让需求实验可按参数和 Python 版本复现.
# English: Generate seeded orders with a private RNG so experiments are reproducible for the same
# parameters and Python version without altering global randomness.
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
