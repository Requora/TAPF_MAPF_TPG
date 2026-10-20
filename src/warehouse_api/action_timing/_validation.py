"""Checks for shared action timing; preserve original errors without catching them."""
from math import isfinite

from warehouse_api.contracts import ActionTimes, Drop, Lift, Serve, TaskAction


# 中文: 拒绝非有限或负时间, 并按需要求正值, 为耗时计算守住数值域, 避免非法步长进入除法.
# English: Reject nonfinite or negative times and require positivity when needed so duration
# arithmetic never divides by an invalid timestep.
def _time(value: float, name: str, *, positive: bool = False) -> None:
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError(f"{name}: expected a finite nonnegative time")
    if positive and value == 0:
        raise ValueError(f"{name}: expected a positive time")


# 中文: 检查耗时模型, 步长和服务数量, 把输入错误隔离在计时边界, 使计算主体只处理合法动作.
# English: Check timing settings, timestep and service quantities at the boundary so the duration
# formula only handles valid actions.
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
