"""Sequential candidate planning. No ledger mutation or Runtime acceptance."""
from dataclasses import replace
from time import monotonic

from ._validation import validate_plan, validate_request
from warehouse_api.contracts import (
    Allocator, ExecutableProposal, Failure, MotionPlanner, MotionRequest,
    PathPlanner, PathRequest, PlanningRequest, SharedCompiler,
)


# 中文: 通过公开协议依次运行分配, 编译, MAPF和TPG, 用一个预算组织候选计算, 保留各阶段独立替换能力.
# English: Compose allocation, compilation, MAPF and TPG through public protocols under one deadline
# so each stage remains independently replaceable.
class StagedPipeline:
    """Allocate, compile, route, and prepare motion under one wall-clock budget.

    Stages must respect their budgets and must not mutate input snapshots.
    Synchronous calls cannot be preempted here; late results are discarded.
    Runtime must validate and atomically accept the returned candidate.
    """

    # 中文: 注入各阶段实现并建立 trace 容器, 将编排与算法选择分开, 便于用真实适配器或明确的测试替身验证边界.
    # English: Inject stage implementations and initialize tracing so orchestration is independent
    # of algorithm choice and can be checked with native adapters or explicit doubles.
    def __init__(self, allocator: Allocator, compiler: SharedCompiler,
                 path_planner: PathPlanner, motion_planner: MotionPlanner):
        self.allocator = allocator
        self.compiler = compiler
        self.path_planner = path_planner
        self.motion_planner = motion_planner
        self.last_trace: list[tuple[str, object, object]] = []

    # 中文: 传递同一请求和递减预算并保留阶段结果, 在失败或到期时停止, 只返回完整候选而不提交实时账本.
    # English: Pass one request with decreasing budgets, record stage results and stop on failure or
    # expiry, returning a complete candidate without committing live state.
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
        # 中文: 分配只提出新任务和队列修改; 当前请求仍是不可修改的已接受状态快照.
        # English: Allocation proposes task/queue edits; the request remains the accepted-state snapshot.
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
        # 中文: 编译器同时读取旧快照和草稿, 保护进度与锁后再给出统一物理动作.
        # English: Compile old state plus the draft so progress and locks are protected before routing.
        jobs = self.compiler.compile_jobs(assignment, draft)
        self.last_trace.append(("compilation", (assignment, draft), jobs))
        if isinstance(jobs, Failure):
            return jobs
        remaining = deadline - monotonic()
        if remaining <= 0:
            return timeout
        # 中文: MAPF 接收编译动作而不是订单; 这里选择路线, 还没有决定真实执行时间.
        # English: MAPF consumes compiled jobs, not orders; it chooses routes rather than physical times.
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
        # 中文: TPG 必须沿同一条路线保留同一组动作, 再计算曲线和完整停车尾段候选.
        # English: TPG retains these routes and actions while constructing motion and a stop-tail candidate.
        motion_request = MotionRequest(
            assignment.start, jobs, plan, request.target_end_s, remaining,
        )
        motion = self.motion_planner.prepare(motion_request)
        self.last_trace.append(("tpg", motion_request, motion))
        if isinstance(motion, Failure):
            return motion
        if monotonic() >= deadline:
            return timeout
        # 中文: 返回完整候选不等于允许执行; 后续 Runtime 仍须独立验证并原子提交.
        # English: Returning a complete candidate does not authorize execution; Runtime must validate and commit.
        return ExecutableProposal(assignment.start.request_id, draft, motion)
