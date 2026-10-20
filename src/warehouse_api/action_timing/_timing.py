"""Pure action timing shared by future compiler and motion-planner adapters."""
from fractions import Fraction
from math import ceil

from ._validation import validate_action_timing
from warehouse_api.contracts import ActionTimes, Drop, Lift, TaskAction


def action_duration_ticks(
    action: TaskAction, times: ActionTimes, *, sim_dt_s: float,
) -> int:
    """Return the minimum whole tick count for a complete action.

    Interpret numeric inputs by their shortest decimal string, as in JSON.
    Evaluate the service formula exactly before rounding up, without epsilon.
    Zero model durations yield zero ticks. This does not compute the remaining
    duration of an action already running at the planning splice.
    """
    validate_action_timing(action, times, sim_dt_s)
    if isinstance(action, Lift):
        duration = Fraction(str(times.lift_s))
    elif isinstance(action, Drop):
        duration = Fraction(str(times.drop_s))
    else:
        units = sum(pick.quantity for pick in action.picks)
        duration = (Fraction(str(times.service_base_s))
                    + units * Fraction(str(times.service_per_unit_s)))
    return ceil(duration / Fraction(str(sim_dt_s)))


def action_duration_s(
    action: TaskAction, times: ActionTimes, *, sim_dt_s: float,
) -> float:
    """Return quantized seconds for PhysicalAction.duration_s.

    Convert the exact decimal tick product to float once. The integer tick
    count is authoritative; seconds have ordinary float representation error.
    An unrepresentable seconds result raises the original OverflowError.
    """
    ticks = action_duration_ticks(action, times, sim_dt_s=sim_dt_s)
    return float(ticks * Fraction(str(sim_dt_s)))
