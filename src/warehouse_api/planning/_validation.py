"""Planning boundary checks, separate from stage algorithms and safety checks."""
from math import isfinite

from warehouse_api.contracts import Failure, FleetPlan, PlanningRequest


def validate_request(request: PlanningRequest) -> Failure | None:
    budget = request.assignment.budget_s
    if not isfinite(budget) or budget <= 0:
        return Failure("BAD_INPUT", "Planning budget must be finite and positive", ())
    if (not isfinite(request.target_end_s)
            or request.target_end_s <= request.assignment.start.join_state.time_s):
        return Failure("BAD_INPUT", "Target end must be after the splice time", ())
    return None


def validate_plan(request: PlanningRequest, plan: FleetPlan) -> Failure | None:
    request_id = request.assignment.start.request_id
    if plan.request_id != request_id:
        return Failure("STALE_REQUEST", "Path result belongs to another request",
                       (request_id, plan.request_id))
    return None
