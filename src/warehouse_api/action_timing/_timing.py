"""中文: 该模块将完整动作耗时向上量化为仿真步数和秒数, 使编译器与运动规划器使用一致时长.

English: This module rounds complete-action durations up to simulation steps and seconds so compilation and motion planning use consistent durations.
"""
from fractions import Fraction
from math import ceil

from ._validation import validate_action_timing
from warehouse_api.contracts import ActionTimes, Drop, Lift, TaskAction


# 中文: action_duration_ticks 用十进制精确计算完整动作需要多少个仿真步长(tick), 并向上取整, 防止浮点误差缩短动作或多加一步等待.
# English: action_duration_ticks computes complete-action duration as an exact decimal count of
# simulation steps (ticks) and rounds up so floating-point error cannot shorten an action or add a
# spurious step.
def action_duration_ticks(
    action: TaskAction, times: ActionTimes, *, sim_dt_s: float,
) -> int:
    """action_duration_ticks returns the minimum whole tick count for a complete action.

    The calculation interprets inputs by their shortest decimal string, as in JSON.
    The function evaluates the service formula exactly before rounding up, without epsilon.
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


# 中文: action_duration_s 将完整动作的整数仿真步数换算为秒, 供 PhysicalAction.duration_s 记录机器人执行动作的耗时,
# 使编译器和运动规划器采用同一量化结果.
# English: action_duration_s converts the complete action's integer simulation-step count into seconds
# for PhysicalAction.duration_s, the robot action duration, so compilation and motion planning use the
# same quantized result.
def action_duration_s(
    action: TaskAction, times: ActionTimes, *, sim_dt_s: float,
) -> float:
    """action_duration_s returns quantized seconds for PhysicalAction.duration_s.

    The function converts the exact decimal tick product to float once. The integer tick
    count is authoritative; seconds have ordinary float representation error.
    An unrepresentable seconds result raises the original OverflowError.
    """
    ticks = action_duration_ticks(action, times, sim_dt_s=sim_dt_s)
    return float(ticks * Fraction(str(sim_dt_s)))
