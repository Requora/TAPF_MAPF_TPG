"""中文: 本模块集中检查曲线与查询范围, 防止轨迹读取静默修正非法输入.
English: This module validates curves and query ranges to prevent silent input repair.
"""
from math import isfinite

from warehouse_api.contracts import Knot, Twist2


# 中文: is_stopped 要求速度的所有分量精确为零, 避免把缓慢运动误当成无限期停车.
# English: is_stopped requires exactly zero velocity components so slow motion cannot become indefinite parking.
def is_stopped(velocity: Twist2) -> bool:
    return velocity == Twist2(0, 0, 0)


# 中文: check_knots 检查有限状态与递增时间, 为曲线计算建立前提, 不证明动力学或碰撞安全.
# English: check_knots checks finite states and increasing times as evaluation prerequisites, not dynamics or collision safety.
def check_knots(knots: tuple[Knot, ...]) -> None:
    if not knots:
        raise ValueError("A curve needs at least one knot")
    for index, knot in enumerate(knots):
        if not all(isfinite(value) for value in (
            knot.time_s, knot.pose.x_m, knot.pose.y_m, knot.pose.yaw_rad,
            knot.velocity.vx_mps, knot.velocity.vy_mps, knot.velocity.omega_radps,
        )):
            raise ValueError("Curve has non-finite values")
        if index and (knot.time_s <= knots[index - 1].time_s
                      or not isfinite(knot.time_s - knots[index - 1].time_s)):
            raise ValueError("Knot intervals must be positive and finite")


# 中文: check_time 检查查询时间覆盖范围, 仅允许静止终点延伸, 防止凭空生成运动.
# English: check_time checks query coverage and permits only stationary terminal extension to avoid inventing motion.
def check_time(knots: tuple[Knot, ...], time_s: float) -> None:
    if not isfinite(time_s) or time_s < knots[0].time_s:
        raise ValueError("Query must be finite and not before curve start")
    if time_s > knots[-1].time_s and not is_stopped(knots[-1].velocity):
        raise ValueError("Moving curve has no terminal hold")


# 中文: check_interval 检查切片两端及正时长, 防止无效区间产生看似可执行的曲线.
# English: check_interval validates slice endpoints and positive duration so invalid intervals cannot look executable.
def check_interval(knots: tuple[Knot, ...], start_s: float, end_s: float) -> None:
    check_time(knots, start_s)
    check_time(knots, end_s)
    if end_s <= start_s or not isfinite(end_s - start_s):
        raise ValueError("Slice duration must be positive and finite")
