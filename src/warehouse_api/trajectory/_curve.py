"""中文: 本模块按 API 0.7 参考包的 Hermite 公式读取原曲线, 不重新规划运动.
English: This module evaluates original curves using API 0.7 reference Hermite formulas without replanning.
"""
from dataclasses import replace

from warehouse_api.contracts import Knot, Pose2, Twist2
from ._validation import check_interval, check_knots, check_time


# 中文: _axis 计算单轴三次 Hermite 位置及其导数, 让三个坐标使用相同运动定义.
# English: _axis evaluates one cubic Hermite coordinate and its derivative so all coordinates share one motion definition.
def _axis(p0: float, v0: float, p1: float, v1: float, h: float, u: float) -> tuple[float, float]:
    position = ((2*u**3 - 3*u**2 + 1)*p0 + (u**3 - 2*u**2 + u)*h*v0
                + (-2*u**3 + 3*u**2)*p1 + (u**3 - u**2)*h*v1)
    velocity = (((6*u*u - 6*u)*p0 + (-6*u*u + 6*u)*p1)/h
                + (3*u*u - 4*u + 1)*v0 + (3*u*u - 2*u)*v1)
    return position, velocity


# 中文: _evaluate 读取已校验曲线, 原样保留节点并计算段内状态, 供批量切片避免重复输入检查.
# English: _evaluate reads a validated curve, preserving knots and evaluating interior states without repeated input checks during slicing.
def _evaluate(knots: tuple[Knot, ...], time_s: float) -> Knot:
    if time_s >= knots[-1].time_s:
        return replace(knots[-1], time_s=time_s)
    for left, right in zip(knots, knots[1:]):
        if time_s == left.time_s:
            return left
        if time_s < right.time_s:
            h = right.time_s - left.time_s
            u = (time_s - left.time_s)/h
            x, vx = _axis(left.pose.x_m, left.velocity.vx_mps, right.pose.x_m, right.velocity.vx_mps, h, u)
            y, vy = _axis(left.pose.y_m, left.velocity.vy_mps, right.pose.y_m, right.velocity.vy_mps, h, u)
            yaw, omega = _axis(left.pose.yaw_rad, left.velocity.omega_radps,
                               right.pose.yaw_rad, right.velocity.omega_radps, h, u)
            result = Knot(time_s, Pose2(x, y, yaw), Twist2(vx, vy, omega))
            check_knots((result,))
            return result
    raise ValueError("Time not covered")


# 中文: evaluate 读取指定时刻的位置与速度, 供验证和执行共用原曲线; 非法输入抛出 ValueError.
# 朝向采用未折返角度, 单节点移动仅可读取该瞬间, 只有精确静止终点允许延伸.
# English: evaluate returns position and velocity for shared validation and execution on the original curve; invalid input raises ValueError.
# Yaw stays unwrapped, moving singletons cover only their instant, and only exactly stopped endpoints extend.
def evaluate(knots: tuple[Knot, ...], time_s: float) -> Knot:
    check_knots(knots)
    check_time(knots, time_s)
    return _evaluate(knots, time_s)


# 中文: slice_curve 保留两端状态及全部内部节点, 使执行区间与原曲线一致, 浮点计算误差除外; 非法输入抛出 ValueError.
# English: slice_curve retains endpoint states and all internal knots to preserve the original execution interval up to floating-point error; invalid input raises ValueError.
def slice_curve(knots: tuple[Knot, ...], start_s: float, end_s: float) -> tuple[Knot, ...]:
    check_knots(knots)
    check_interval(knots, start_s, end_s)
    return (_evaluate(knots, start_s), *(knot for knot in knots if start_s < knot.time_s < end_s),
            _evaluate(knots, end_s))
