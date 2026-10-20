"""Planning boundary checks, separate from stage algorithms and safety checks."""
from math import isfinite

from warehouse_api.contracts import Do, Failure, FleetPlan, PlanningRequest, RobotJobs


def validate_request(request: PlanningRequest) -> Failure | None:
    budget = request.assignment.budget_s
    if not isfinite(budget) or budget <= 0:
        return Failure("BAD_INPUT", "Planning budget must be finite and positive", ())
    if (not isfinite(request.target_end_s)
            or request.target_end_s <= request.assignment.start.join_state.time_s):
        return Failure("BAD_INPUT", "Target end must be after the splice time", ())
    return None


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
