"""中文: 该模块校验订单生成和重放的输入, 使错误在改变发布状态前直接暴露.

English: This module validates order-generation and replay inputs so errors surface before release state changes.
"""
from math import isfinite

from warehouse_api.contracts import Order


# 中文: _time 检查订单时间是否有限且非负, 在发布和生成前拒绝非法值, 使订单排序和已发布位置仍有明确的时间含义.
# English: _time checks that order times are finite and nonnegative before release or generation so order
# sorting and release progress retain a meaningful time basis.
def _time(value: float, name: str) -> None:
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError(f"{name}: expected a finite nonnegative time")


# 中文: _identifier 拒绝空白订单标识和商品编号(SKU), 使订单需求在归并后仍能对应到原订单和商品.
# English: _identifier rejects blank order identifiers and stock-keeping unit (SKU) identifiers so merged
# demand remains traceable to its order and item.
def _identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: expected a nonblank string")


# 中文: _positive_int 拒绝布尔值和非正整数件数, 使商品数量保持计数含义, 防止无效需求进入服务耗时计算.
# English: _positive_int rejects booleans and nonpositive item counts so quantities retain integer-count
# semantics before service-duration calculation.
def _positive_int(value: int, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name}: expected a positive integer")


# 中文: validate_orders 在替换订单发布状态前校验整批订单的唯一标识, 时间和商品需求, 防止重放器只接受非法序列的一部分.
# English: validate_orders checks identifiers for uniqueness, times and item demand across the full batch
# before release-state replacement so the replay source cannot partially accept an invalid sequence.
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


# 中文: validate_release_time 拒绝非有限, 负值或倒退的发布截止时间, 保证已发布位置只前进, 防止历史订单再次被当成新需求.
# English: validate_release_time rejects nonfinite, negative or backward release cutoffs so release
# progress moves forward and past orders cannot become new demand again.
def validate_release_time(until_s: float, previous_s: float) -> None:
    _time(until_s, "until_s")
    if until_s < previous_s:
        raise ValueError(f"until_s: time moved backward from {previous_s} to {until_s}")


# 中文: validate_generation_parameters 在生成订单前检查随机种子, 商品编号(SKU), 件数和最后一个订单的时间范围,
# 让无效或溢出配置在产生部分订单前失败.
# English: validate_generation_parameters checks the random seed, stock-keeping unit (SKU) identifiers,
# quantities and final-order time bounds before generation so invalid or overflowing settings fail before
# a partial order sequence is built.
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
