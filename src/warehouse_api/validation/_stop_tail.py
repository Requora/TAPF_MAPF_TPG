"""中文: 本模块检查停车候选的结构, 为后续连续几何和动作验证提供明确前置条件.
English: This module checks stopping-candidate structure as a prerequisite for continuous geometry and action validation.
"""
from math import isfinite

from warehouse_api.contracts import (
    Failure, MotionPlan, PlanningStart, RobotSegment, Twist2, WorldModel,
)


# 中文: check_motion_curve 检查候选节点的有限值和时间顺序, 使结构错误返回失败原因而非进入插值计算.
# English: check_motion_curve checks finite values and ordered times so malformed candidates return reasons before interpolation.
def check_motion_curve(segment: RobotSegment) -> Failure | None:
    previous = None
    for knot in segment.knots:
        values = (knot.time_s, knot.pose.x_m, knot.pose.y_m, knot.pose.yaw_rad,
                  knot.velocity.vx_mps, knot.velocity.vy_mps, knot.velocity.omega_radps)
        if not all(isfinite(value) for value in values):
            return Failure('BAD_INPUT', 'Non-finite motion knot', (segment.robot_id,))
        if previous is not None and (knot.time_s <= previous or not isfinite(knot.time_s - previous)):
            return Failure('BAD_INPUT', 'Motion times must strictly increase with finite intervals', (segment.robot_id,))
        previous = knot.time_s
    if not segment.knots:
        return Failure('BAD_INPUT', 'Motion segment has no knots', (segment.robot_id,))
    return None


# 中文: check_stop_tail_structure 核对完整车队, 共同前缀边界, 精确状态衔接和零终速, 为后续安全门禁排除结构错误; 本函数不验证几何, 动作或制动能力, 返回空元组不表示可提交.
# English: check_stop_tail_structure checks fleet coverage, common prefix horizon, exact state joins and zero terminal speeds before later safety gates; it does not check geometry, actions or braking feasibility, and an empty result does not authorize submission.
def check_stop_tail_structure(model: WorldModel, start: PlanningStart,
                              motion: MotionPlan) -> tuple[Failure, ...]:
    robot_ids = tuple(robot.id for robot in model.robots)
    state_ids = tuple(robot.robot_id for robot in start.join_state.robots)
    if not robot_ids or len(set(robot_ids)) != len(robot_ids):
        return (Failure('BAD_INPUT', 'Model requires distinct robot IDs', robot_ids),)
    for label, ids in (
        ('join state', state_ids),
        ('common prefix', tuple(segment.robot_id for segment in motion.common_prefix)),
        ('stop tail', tuple(segment.robot_id for segment in motion.stop_tail)),
    ):
        if len(ids) != len(robot_ids) or set(ids) != set(robot_ids):
            return (Failure('BAD_INPUT', f'{label} must cover each model robot exactly once', ids + robot_ids),)
    if not isfinite(start.join_state.time_s):
        return (Failure('BAD_INPUT', 'Join time must be finite', robot_ids),)
    errors = tuple(error for segment in (*motion.common_prefix, *motion.stop_tail)
                   if (error := check_motion_curve(segment)) is not None)
    if errors:
        return errors
    states = {robot.robot_id: robot for robot in start.join_state.robots}
    tails = {segment.robot_id: segment for segment in motion.stop_tail}
    horizon = motion.common_prefix[0].knots[-1].time_s
    failures = []
    for prefix in motion.common_prefix:
        robot_id = prefix.robot_id
        state = states[robot_id]
        first, last = prefix.knots[0], prefix.knots[-1]
        tail = tails[robot_id]
        if (first.time_s != start.join_state.time_s or first.pose != state.pose
                or first.velocity != state.velocity):
            failures.append(Failure('BAD_INPUT', 'Prefix must exactly match join state', (robot_id,)))
        if last.time_s != horizon:
            failures.append(Failure('BAD_INPUT', 'Prefixes must share one end time', (robot_id,)))
        if tail.knots[0] != last:
            failures.append(Failure('BAD_INPUT', 'Stop tail must exactly match prefix endpoint', (robot_id,)))
        if tail.knots[-1].velocity != Twist2(0, 0, 0):
            failures.append(Failure('BAD_INPUT', 'Stop tail must end with zero linear and angular velocity', (robot_id,)))
    return tuple(failures)
