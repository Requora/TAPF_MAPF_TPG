"""中文: 该模块集中检查规划请求和阶段输出, 使流程编排无需内联输入规则; 这些检查不承担连续运动安全验收.

English: This module checks planning requests and stage output centrally so orchestration need not inline input rules; these checks do not perform continuous-motion safety acceptance.
"""
from math import isfinite

from warehouse_api.contracts import Do, Failure, FleetPlan, PlanningRequest, RobotJobs


# 中文: validate_request 在任何规划阶段启动前检查总计算时间预算和期望规划结束时刻, 防止负预算或不晚于方案接入时刻的结束时间传播到后续求解器.
# English: validate_request checks the total computation budget and desired planning end time before any
# stage starts so invalid budgets or end times at or before the plan's join time cannot reach later solvers.
def validate_request(request: PlanningRequest) -> Failure | None:
    budget = request.assignment.budget_s
    if not isfinite(budget) or budget <= 0:
        return Failure("BAD_INPUT", "Planning budget must be finite and positive", ())
    if (not isfinite(request.target_end_s)
            or request.target_end_s <= request.assignment.start.join_state.time_s):
        return Failure("BAD_INPUT", "Target end must be after the splice time", ())
    return None


# 中文: validate_plan 核对路径结果的请求标识, 机器人覆盖和任务步骤引用顺序, 防止过期路线或错误任务进入 TPG 运动时序规划; 该检查不证明连续运动的几何安全.
# English: validate_plan checks a path result's request identifier, robot coverage and task-step
# reference order so stale routes or incorrect tasks cannot reach TPG motion timing; this check does not
# prove continuous-motion geometry safety.
def validate_plan(request: PlanningRequest, jobs: tuple[RobotJobs, ...],
                  plan: FleetPlan) -> Failure | None:
    request_id = request.assignment.start.request_id
    if plan.request_id != request_id:
        return Failure("STALE_REQUEST", "Path result belongs to another request",
                       (request_id, plan.request_id))
    expected = {job.robot_id: tuple(action.step for action in job.actions) for job in jobs}
    robot_ids = [route.robot_id for route in plan.routes]
    if len(set(robot_ids)) != len(robot_ids) or set(robot_ids) != set(expected):
        return Failure("BAD_INPUT", "Path result must cover each compiled robot once", tuple(robot_ids))
    for route in plan.routes:
        actions = tuple(step.step for step in route.steps if isinstance(step, Do))
        if actions != expected[route.robot_id]:
            return Failure("BAD_INPUT", "Path actions differ from compiled jobs", (route.robot_id,))
    return None
