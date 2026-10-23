"""中文: 该模块顺序计算完整候选方案, 使各阶段共享时间预算; Runtime 运行协调模块仍负责验收与账本提交.

English: This module computes complete candidates sequentially so stages share a time budget; the Runtime coordination module remains responsible for acceptance and ledger commits.
"""
from dataclasses import replace
from time import monotonic

from ._validation import validate_motion, validate_plan, validate_request
from warehouse_api.contracts import (
    Allocator, ExecutableProposal, Failure, MotionPlanner, MotionRequest,
    PathPlanner, PathRequest, PlanningRequest, SharedCompiler,
)


# 中文: StagedPipeline 通过模块间的协议依次调用任务分配, 动作编译, MAPF 多机器人路径规划和 TPG 运动时序规划, 用同一计算时间预算组织候选方案,
# 让各阶段可独立替换.
# English: StagedPipeline calls allocation, action compilation, MAPF multi-agent path finding and TPG
# motion timing through inter-module protocols under one computation budget so each candidate-planning
# stage remains independently replaceable.
class StagedPipeline:
    """StagedPipeline allocates, compiles, routes and prepares motion under one wall-clock budget.

    Stages must respect their budgets and must not mutate input snapshots.
    Synchronous calls cannot be preempted here; late results are discarded.
    Runtime must validate and atomically accept the returned candidate.
    """

    # 中文: StagedPipeline.__init__ 保存调用方选定的各阶段实现, 并创建 last_trace 来记录阶段请求和结果, 将流程编排与算法选择分开,
    # 便于检查真实适配器或测试替身的交互.
    # English: StagedPipeline.__init__ stores the supplied stage implementations and creates last_trace
    # to record stage requests and results so orchestration stays separate from algorithm choice and
    # native-adapter or test-double interactions remain inspectable.
    def __init__(self, allocator: Allocator, compiler: SharedCompiler,
                 path_planner: PathPlanner, motion_planner: MotionPlanner):
        self.allocator = allocator
        self.compiler = compiler
        self.path_planner = path_planner
        self.motion_planner = motion_planner
        self.last_trace: list[tuple[str, object, object]] = []

    # 中文: solve 将同一规划请求和剩余计算时间传给各阶段, 记录中间结果并检查运动结构, 在失败或超时后停止, 使调用方只收到结构完整的候选方案. 该方法不提交库存, 任务进度等实时账本.
    # English: solve passes the same planning request and remaining computation time through the stages,
    # records intermediate results, checks motion structure and stops on failure or timeout so callers receive complete
    # candidates; the method does not commit live records such as stock or task progress.
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
        # 中文: 编译器同时读取已接受状态快照和候选任务草稿, 保留进度与执行者锁定后生成统一执行动作.
        # English: The compiler reads accepted state and the task draft to preserve progress and executor locks before routing.
        jobs = self.compiler.compile_jobs(assignment, draft)
        self.last_trace.append(("compilation", (assignment, draft), jobs))
        if isinstance(jobs, Failure):
            return jobs
        remaining = deadline - monotonic()
        if remaining <= 0:
            return timeout
        # 中文: MAPF 路径规划器接收编译器生成的执行动作, 据此选择到达路线; 该阶段尚不决定真实执行时间.
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
        # 中文: TPG 运动规划器沿选定路线保留同一组动作, 再计算运动曲线与使机器人最终停稳的尾段候选.
        # English: TPG retains these routes and actions while constructing motion and a stop-tail candidate.
        motion_request = MotionRequest(
            assignment.start, jobs, plan, request.target_end_s, remaining,
        )
        motion = self.motion_planner.prepare(motion_request)
        self.last_trace.append(("tpg", motion_request, motion))
        if isinstance(motion, Failure):
            return motion
        failure = validate_motion(request, motion)
        if failure is not None:
            return failure
        if monotonic() >= deadline:
            return timeout
        # 中文: solve 返回的完整候选尚未获准执行; Runtime 运行协调模块仍须独立验证, 并一次性提交完整方案.
        # English: solve returns an unaccepted candidate; the Runtime coordination module must validate it and commit the complete plan atomically.
        return ExecutableProposal(assignment.start.request_id, draft, motion)
