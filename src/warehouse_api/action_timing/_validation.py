"""中文: 该模块集中检查动作耗时输入, 使非法时间及数量在计算前失败并保留原始异常.

English: This module checks action-timing inputs centrally so invalid times and quantities fail before calculation with their original errors.
"""
from math import isfinite

from warehouse_api.contracts import ActionTimes, Drop, Lift, Serve, TaskAction


# 中文: _time 检查时间值是否有限且非负, 并按调用要求排除零值, 防止耗时计算使用非法时间或除以零步长.
# English: _time checks that a time is finite and nonnegative, excluding zero when requested, so duration
# arithmetic cannot use invalid times or divide by a zero timestep.
def _time(value: float, name: str, *, positive: bool = False) -> None:
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError(f"{name}: expected a finite nonnegative time")
    if positive and value == 0:
        raise ValueError(f"{name}: expected a positive time")


# 中文: validate_action_timing 检查动作类型, 耗时参数, 仿真步长和服务件数, 在计算入口拒绝错误输入, 使耗时公式只处理支持的动作.
# English: validate_action_timing checks action types, timing parameters, simulation timesteps and
# service quantities at the calculation boundary so duration formulas only process supported actions.
def validate_action_timing(
    action: TaskAction, times: ActionTimes, sim_dt_s: float,
) -> None:
    _time(sim_dt_s, "sim_dt_s", positive=True)
    for name in ("lift_s", "drop_s", "service_base_s", "service_per_unit_s"):
        _time(getattr(times, name), f"action_times.{name}")
    if type(action) not in (Lift, Serve, Drop):
        raise TypeError("action: expected Lift, Serve, or Drop")
    expected = {Lift: "lift", Serve: "serve", Drop: "drop"}[type(action)]
    if action.kind != expected:
        raise ValueError(f"action.kind: expected {expected}")
    if isinstance(action, Serve):
        if not action.picks:
            raise ValueError("serve.picks: expected at least one pick")
        for pick in action.picks:
            if type(pick.quantity) is not int or pick.quantity <= 0:
                raise ValueError("pick.quantity: expected a positive integer")
