"""中文: 本模块集中检查执行输入, 防止切片主体隐藏曲线和动作错误.
English: This module centralizes execution-input checks so slicing does not hide curve or action errors.
"""
from math import isfinite, isclose

from warehouse_api.contracts import ExecutionInput, Failure, RobotSegment, Twist2
from warehouse_api.validation import check_motion_curve


# 中文: same_tick 仅为动作时钟比较容许至多 1 ns 且小于百万分之一步的舍入误差, 防止浮点累加漏发; 本函数不放宽位姿衔接.
# English: same_tick allows at most 1 ns and one millionth of a tick for action-clock roundoff, preventing dropped starts without relaxing pose joins.
def same_tick(a: float, b: float, dt_s: float) -> bool:
    return isclose(a, b, rel_tol=0, abs_tol=min(1e-9, dt_s * 1e-6))


# 中文: check_input 检查完整车队, 控制时间和动作引用, 让执行器只转换结构有效的输入; 本函数不证明动作业务或几何安全.
# English: check_input checks fleet coverage, control times and action references before conversion; it does not prove business or geometric safety.
def check_input(data: ExecutionInput, dt_s: float) -> Failure | None:
    now = data.state.time_s
    if not isfinite(now) or not isfinite(dt_s) or dt_s <= 0 or not isfinite(now + dt_s) or now + dt_s <= now:
        return Failure('BAD_FRAME', 'Control interval must be finite and positive', ())
    robots = tuple(robot.robot_id for robot in data.state.robots)
    segments = tuple(segment.robot_id for segment in data.active_segments)
    if not robots or len(set(robots)) != len(robots) or len(segments) != len(robots) or set(segments) != set(robots):
        return Failure('BAD_FRAME', 'Segments must cover every state robot exactly once', robots)
    table = {action.step: action for action in data.action_table}
    if len(table) != len(data.action_table):
        return Failure('BAD_ACTION', 'Action table has duplicate step references', ())
    seen = set()
    running = {action.step: action for action in data.state.running_actions}
    for segment in data.active_segments:
        starts = 0
        for scheduled in segment.actions:
            if scheduled.step not in table or scheduled.step in seen or not isfinite(scheduled.start_s):
                return Failure('BAD_ACTION', 'Scheduled steps must be finite, unique and defined', (segment.robot_id,))
            seen.add(scheduled.step)
            action = table[scheduled.step]
            if not isfinite(action.duration_s) or action.duration_s <= 0:
                return Failure('BAD_ACTION', 'Action duration must be finite and positive', (segment.robot_id,))
            if (now < scheduled.start_s < now + dt_s
                    and not same_tick(scheduled.start_s, now, dt_s)
                    and not same_tick(scheduled.start_s, now + dt_s, dt_s)):
                return Failure('BAD_FRAME', 'Action starts inside a control step; use an aligned timestep', (segment.robot_id,))
            active = running.get(scheduled.step)
            if active is not None and active.robot_id != segment.robot_id:
                return Failure('BAD_ACTION', 'Running action belongs to another robot', (segment.robot_id,))
            new_start = same_tick(scheduled.start_s, now, dt_s) and active is None
            if new_start and any(item.robot_id == segment.robot_id for item in data.state.running_actions):
                return Failure('BAD_ACTION', 'Robot already has a running action', (segment.robot_id,))
            starts += new_start
        if starts > 1:
            return Failure('BAD_ACTION', 'A robot cannot start multiple actions in one step', (segment.robot_id,))
    return None


# 中文: check_curve 检查新曲线的节点与时间结构, 将执行边界错误映射为 BAD_FRAME, 避免原生切片收到无效节点.
# English: check_curve checks new curve structure and maps execution-boundary errors to BAD_FRAME before native slicing.
def check_curve(segment: RobotSegment) -> Failure | None:
    failure = check_motion_curve(segment)
    if failure is not None:
        return Failure('BAD_FRAME', failure.message, failure.related_ids)
    return None


# 中文: check_coverage 禁止移动终点外推, 仅允许静止终点保持, 确保下一帧在选定计划的有效时间内.
# English: check_coverage forbids moving-endpoint extrapolation and permits stopped holds so each frame stays within selected-plan coverage.
def check_coverage(segment: RobotSegment, start_s: float, end_s: float) -> Failure | None:
    if start_s < segment.knots[0].time_s or (end_s > segment.knots[-1].time_s
                                             and segment.knots[-1].velocity != Twist2(0, 0, 0)):
        return Failure('BAD_FRAME', 'Selected motion does not cover the control interval', (segment.robot_id,))
    return None
