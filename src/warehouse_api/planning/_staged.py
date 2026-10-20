"""Sequential candidate planning. No ledger mutation or Runtime acceptance."""
from dataclasses import replace
from time import monotonic

from ._validation import validate_plan, validate_request
from warehouse_api.contracts import (
    Allocator, ExecutableProposal, Failure, MotionPlanner, MotionRequest,
    PathPlanner, PathRequest, PlanningRequest, SharedCompiler,
)


class StagedPipeline:
    """Allocate, compile, route, and prepare motion under one wall-clock budget.

    Stages must respect their budgets and must not mutate input snapshots.
    Synchronous calls cannot be preempted here; late results are discarded.
    Runtime must validate and atomically accept the returned candidate.
    """

    def __init__(self, allocator: Allocator, compiler: SharedCompiler,
                 path_planner: PathPlanner, motion_planner: MotionPlanner):
        self.allocator = allocator
        self.compiler = compiler
        self.path_planner = path_planner
        self.motion_planner = motion_planner
        self.last_trace: list[tuple[str, object, object]] = []

    def solve(self, request: PlanningRequest) -> ExecutableProposal | Failure:
        started = monotonic()
        self.last_trace = []
        failure = validate_request(request)
        if failure is not None:
            return failure
        assignment = request.assignment
        deadline = started + assignment.budget_s
        timeout = Failure("TIMEOUT", "Shared planning budget exhausted",
                          (assignment.start.request_id,))
        remaining = deadline - monotonic()
        if remaining <= 0:
            return timeout
        allocation_request = replace(assignment, budget_s=remaining)
        draft = self.allocator.allocate(allocation_request)
        self.last_trace.append(("allocation", allocation_request, draft))
        if isinstance(draft, Failure):
            return draft
        if monotonic() >= deadline:
            return timeout
        jobs = self.compiler.compile_jobs(assignment, draft)
        self.last_trace.append(("compilation", (assignment, draft), jobs))
        if isinstance(jobs, Failure):
            return jobs
        remaining = deadline - monotonic()
        if remaining <= 0:
            return timeout
        path_request = PathRequest(assignment.start, jobs, remaining)
        plan = self.path_planner.plan(path_request)
        self.last_trace.append(("mapf", path_request, plan))
        if isinstance(plan, Failure):
            return plan
        failure = validate_plan(request, jobs, plan)
        if failure is not None:
            return failure
        remaining = deadline - monotonic()
        if remaining <= 0:
            return timeout
        motion_request = MotionRequest(
            assignment.start, jobs, plan, request.target_end_s, remaining,
        )
        motion = self.motion_planner.prepare(motion_request)
        self.last_trace.append(("tpg", motion_request, motion))
        if isinstance(motion, Failure):
            return motion
        if monotonic() >= deadline:
            return timeout
        return ExecutableProposal(assignment.start.request_id, draft, motion)
