"""Checks for shared action timing; preserve original errors without catching them."""
from math import isfinite

from warehouse_api.contracts import ActionTimes, Drop, Lift, Serve, TaskAction


def _time(value: float, name: str, *, positive: bool = False) -> None:
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        raise ValueError(f"{name}: expected a finite nonnegative time")
    if positive and value == 0:
        raise ValueError(f"{name}: expected a positive time")


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
