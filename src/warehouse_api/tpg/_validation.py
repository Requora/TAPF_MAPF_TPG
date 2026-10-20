"""Check route/action correspondence and exported upstream speed primitives."""
from math import isclose, isfinite

from warehouse_api.contracts import Do, Failure, MotionRequest, Move, WorldModel


def check_route(model: WorldModel, request: MotionRequest, sim_dt_s: float) -> Failure | None:
    plan = request.fleet_plan
    if not isfinite(sim_dt_s) or sim_dt_s <= 0:
        raise ValueError("sim_dt_s must be finite and positive")
    if plan.request_id != request.start.request_id:
        return Failure("STALE_REQUEST", "TPG path request ID mismatch", ())
    if len(plan.routes) != 1 or plan.routes[0].robot_id != model.robots[0].id or plan.before:
        return Failure("UNSUPPORTED", "TPG subset requires a single route without cross-robot precedence", ())
    edges = {edge.id: edge for edge in model.edges}
    current = min(model.nodes, key=lambda node: node.position.x_m).id
    index = 0
    for step in plan.routes[0].steps:
        if isinstance(step, Move):
            if step.edge_id not in edges or edges[step.edge_id].from_node != current:
                return Failure("BAD_INPUT", "Route is not contiguous", ())
            current = edges[step.edge_id].to_node
        elif isinstance(step, Do):
            if index >= 3:
                return Failure("BAD_INPUT", "Route repeats completed actions", ())
            action = request.jobs[0].actions[index]
            if step.step != action.step or current != action.target_node:
                return Failure("BAD_INPUT", "Route does not execute the compiled action at its target", ())
            index += 1
        else:
            return Failure("UNSUPPORTED", "Native lane adapter does not support turns", ())
    if index != 3 or not isinstance(plan.routes[0].steps[-1], Do):
        return Failure("BAD_INPUT", "Route must end with the final compiled action", ())
    return None


def check_profile(rows: list[tuple[float, ...]], moves: int) -> Failure | None:
    failure = Failure("BACKEND_ERROR", "WinkTPG profile violates the supported motion primitives", ())
    if len(rows) != moves or not rows or rows[0][2] != 0 or rows[-1][3] != 0:
        return failure
    previous_end, previous_speed = 0.0, 0.0
    for start, duration, v0, v1 in rows:
        if (not all(isfinite(value) for value in (start, duration, v0, v1))
                or duration <= 0 or start < previous_end - 1e-8
                or not isclose(v0, previous_speed, abs_tol=1e-8)
                or not 0 <= v0 <= 2 or not 0 <= v1 <= 2
                or (start > previous_end + 1e-8 and v0 != 0)):
            return failure
        if v0 == v1 == 0:
            valid = isclose(duration, 2, abs_tol=1e-8)
        else:
            valid = (isclose((v0 + v1) * duration / 2, 1, abs_tol=1e-8)
                     and abs(v1 - v0) / duration <= 1 + 1e-8)
        if not valid:
            return failure
        previous_end, previous_speed = start + duration, v1
    return None
