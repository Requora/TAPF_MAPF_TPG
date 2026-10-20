"""Pure action timing shared by future compiler and motion-planner adapters."""
from fractions import Fraction
from math import ceil

from ._validation import validate_action_timing
from warehouse_api.contracts import ActionTimes, Drop, Lift, TaskAction


# 中文: 用十进制精确计算完整动作所需 tick 数, 集中处理向上量化, 防止浮点误差让动作少执行或多等一拍.
# English: Compute whole-action ticks with exact decimal arithmetic and ceiling so rounding neither
# shortens an action nor adds a spurious tick.
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


# 中文: 把统一 tick 数转成秒, 作为物理动作耗时入口, 让编译器和运动层使用同一个量化结果.
# English: Convert the authoritative tick count to seconds so compilation and motion use the same
# quantized action duration.
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
