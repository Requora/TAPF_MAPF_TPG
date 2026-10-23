"""中文: 本模块在 Python 契约与 C++ 曲线快照之间转换, 避免暴露原生数据对象.
English: This module converts shared Python contracts to C++ curve snapshots without exposing native data objects.
"""
from warehouse_api.contracts import Knot, Pose2, Twist2
from . import _native


# 中文: PreparedTrajectory 拷贝并校验已有轨迹一次, 为高频查询保留原生快照; 它不生成新轨迹.
# English: PreparedTrajectory copies and validates an existing trajectory once for repeated native queries; it does not plan motion.
class PreparedTrajectory:
    # 中文: 构造函数显式读取契约字段并创建独立 C++ 数据, 防止后续查询重复转换节点.
    # English: The constructor explicitly reads contract fields into independent C++ data to avoid repeated knot conversion.
    def __init__(self, knots: tuple[Knot, ...]):
        self._curve = _native.Curve([(k.time_s, k.pose.x_m, k.pose.y_m, k.pose.yaw_rad,
                                     k.velocity.vx_mps, k.velocity.vy_mps, k.velocity.omega_radps) for k in knots])


# 中文: _knot 将原生标量结果还原为统一契约, 使调用方不依赖 C++ 私有编码.
# English: _knot restores shared contracts from native scalars so callers do not depend on private C++ encoding.
def _knot(row) -> Knot:
    return Knot(row[0], Pose2(*row[1:4]), Twist2(*row[4:7]))


# 中文: evaluate 读取 C++ 原曲线的位置和导数; tuple 输入每次转换, 预备快照可复用, 非法值抛出 ValueError.
# English: evaluate reads position and derivative from the C++ curve; tuple inputs convert per call, prepared snapshots are reusable, and invalid values raise ValueError.
def evaluate(knots: tuple[Knot, ...] | PreparedTrajectory, time_s: float) -> Knot:
    curve = knots if isinstance(knots, PreparedTrajectory) else PreparedTrajectory(knots)
    return _knot(curve._curve.evaluate(time_s))


# 中文: slice_curve 通过 C++ 保留两端和全部内部节点, 浮点误差外保持原曲线; 非法区间抛出 ValueError.
# English: slice_curve uses C++ to retain endpoints and all internal knots, preserving the original curve up to floating-point error; invalid intervals raise ValueError.
def slice_curve(knots: tuple[Knot, ...] | PreparedTrajectory, start_s: float, end_s: float) -> tuple[Knot, ...]:
    curve = knots if isinstance(knots, PreparedTrajectory) else PreparedTrajectory(knots)
    return tuple(_knot(row) for row in curve._curve.slice(start_s, end_s))
