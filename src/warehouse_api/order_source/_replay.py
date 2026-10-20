"""中文: 该模块生成并重放订单需求, 使实验可复现且不修改库存, 任务分配或运行状态.

English: This module generates and replays order demand so experiments remain reproducible without modifying stock, allocation or runtime state.
"""
from random import Random

from ._validation import (
    validate_generation_parameters,
    validate_orders,
    validate_release_time,
)
from warehouse_api.contracts import Item, Order


# 中文: ReplayOrderSource 按仿真时间各发布一次订单, 并用可重置的游标记录已发布位置, 让实验能够重放同一需求序列. 该类不预留库存或分配机器人.
# English: ReplayOrderSource releases each order once by simulation time and records release progress
# with a resettable cursor so experiments can replay the same demand sequence; the class does not reserve
# stock or assign robots.
class ReplayOrderSource:
    """ReplayOrderSource implements OrderSource with an inclusive, monotonic release cursor."""

    # 中文: ReplayOrderSource.__init__ 通过 reset 建立初始订单序列, 让首次构造和后续重放采用相同的输入检查及订单归并规则.
    # English: ReplayOrderSource.__init__ builds the initial order sequence through reset so construction
    # and later replay use the same input checks and order-normalization rules.
    def __init__(self, orders: tuple[Order, ...] = ()) -> None:
        self.reset(orders)

    # 中文: reset 先校验全部订单, 再合并相同商品编号(SKU)的需求并排序, 最后重置已发布位置, 避免非法的新序列破坏旧重放状态.
    # English: reset validates all orders, merges demand with the same stock-keeping unit (SKU)
    # identifier and sorts the orders before resetting release progress, so an invalid sequence cannot
    # destroy the old replay state.
    def reset(self, orders: tuple[Order, ...]) -> None:
        """reset validates all orders before replacing the current replay state."""
        validate_orders(orders)
        normalized = []
        for order in orders:
            quantities: dict[str, int] = {}
            for item in order.items:
                quantities[item.sku] = quantities.get(item.sku, 0) + item.quantity
            items = tuple(Item(sku, quantity) for sku, quantity in sorted(quantities.items()))
            normalized.append(Order(order.id, order.released_at_s, items, order.due_at_s))
        # 中文: 排序键用发布时间和 ID 消除同刻歧义, 保证订单重放顺序稳定.
        # English: The sorting lambda uses release time and ID so simultaneous releases replay deterministically.
        self._orders = tuple(sorted(normalized, key=lambda order: (order.released_at_s, order.id)))
        self._cursor = 0
        self._until_s = 0.0

    # 中文: release 返回发布时间不晚于 until_s 且尚未发布的订单, 然后推进已发布位置, 使重复调用不会重复产生需求; 非法时间不会改变发布进度.
    # English: release returns unpublished orders whose release time is at or before until_s and advances
    # release progress so repeated calls cannot duplicate demand; invalid times leave progress unchanged.
    def release(self, until_s: float) -> tuple[Order, ...]:
        """release returns each newly releasable order once; invalid calls leave the cursor intact."""
        validate_release_time(until_s, self._until_s)
        end = self._cursor
        while end < len(self._orders) and self._orders[end].released_at_s <= until_s:
            end += 1
        released = self._orders[self._cursor:end]
        self._cursor = end
        self._until_s = until_s
        return released


# 中文: generate_orders 用 seed 初始化独立的随机数发生器, 按给定商品编号, 件数和发布时间参数生成订单,
# 让相同 Python 版本的实验可复现且不改变全局随机状态.
# English: generate_orders initializes a private random-number generator with seed and generates orders
# from the supplied item identifiers, quantities and release parameters so experiments are reproducible
# on the same Python version without changing global randomness.
def generate_orders(
    *,
    seed: int,
    count: int,
    skus: tuple[str, ...],
    release_interval_s: float = 1.0,
    max_quantity: int = 5,
    due_after_s: float | None = None,
) -> tuple[Order, ...]:
    """generate_orders creates demand using a private random generator and explicit parameters.

    The function releases order i at i * release_interval_s, starting at zero.
    It chooses a uniform item count in [1, len(skus)], samples distinct item
    identifiers and chooses each quantity uniformly in [1, max_quantity]. IDs are order-0, order-1,
    etc. A due offset of None disables deadlines. Reproducibility requires
    the same parameters and Python version; saved orders support replay on other versions.
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
