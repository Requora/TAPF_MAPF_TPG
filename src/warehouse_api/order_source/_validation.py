"""Input validation for order replay and generation; errors propagate directly."""
from math import isfinite

from warehouse_api.contracts import Order


# 中文: 统一检查订单时间是有限非负数, 在发布和生成前排除非法时间, 避免游标与排序失去意义.
# English: Check that order times are finite and nonnegative before release or generation so cursor
# ordering remains meaningful.
def _time(value: float, name: str) -> None:
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError(f"{name}: expected a finite nonnegative time")


# 中文: 拒绝空白标识, 为订单和 SKU 提供基本输入约束, 防止后续归并时无法追溯需求来源.
# English: Reject blank identifiers so orders and SKUs remain traceable when demand is normalized
# and merged.
def _identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: expected a nonblank string")


# 中文: 拒绝布尔值和非正件数, 让商品数量保持明确整数语义, 避免无效需求进入服务耗时计算.
# English: Reject booleans and nonpositive quantities so item counts retain integer meaning before
# service-duration calculation.
def _positive_int(value: int, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name}: expected a positive integer")


# 中文: 校验整批订单 ID, 时间和需求, 在替换发布状态前一次完成, 防止部分接受非法订单序列.
# English: Validate the full order batch before replacing release state so invalid IDs, times or
# demand cannot be partially accepted.
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


# 中文: 禁止非有限时间和倒退发布, 保证游标只向前推进, 避免历史订单被误认为新需求.
# English: Reject invalid or backward release times so the cursor advances monotonically and past
# orders cannot become new demand again.
def validate_release_time(until_s: float, previous_s: float) -> None:
    _time(until_s, "until_s")
    if until_s < previous_s:
        raise ValueError(f"until_s: time moved backward from {previous_s} to {until_s}")


# 中文: 在随机生成前检查种子, SKU 和时间边界, 及早暴露不可复现或溢出的配置, 避免生成到一半才失败.
# English: Validate seed, catalog and time bounds before generation so invalid or overflowing
# configurations fail before a partial schedule is built.
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
