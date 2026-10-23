"""中文: 本模块编排联合候选与共享动作编译, 保持运动规划和 Runtime 验收边界.

English: This module composes joint candidates with shared action compilation, retaining motion and Runtime acceptance boundaries.
"""
from dataclasses import replace
from time import monotonic

from warehouse_api.contracts import (
    ExecutableProposal, Failure, JointPlanner, MotionPlanner, MotionRequest,
    PlanningRequest, SharedCompiler,
)
from ._validation import validate_plan, validate_request


class JointPipeline:
    """中文: JointPipeline 用联合求解替换独立分配和路径阶段, 保留共享编译以核对业务语义.

    English: JointPipeline replaces separate assignment and routing with joint search and retains shared compilation to check business semantics.
    The injected solver must use the same compiler semantics while searching. Recompilation checks
    its final draft; it does not validate geometry or make unsupported native actions expressible.
    """

    def __init__(self, joint_planner: JointPlanner, compiler: SharedCompiler,
                 motion_planner: MotionPlanner):
        """中文: __init__ 保存可替换的阶段并建立请求结果记录, 使联合候选的传播可检查.

        English: __init__ stores replaceable stages and creates an I/O trace so candidate propagation is inspectable.
        """
        self.joint_planner = joint_planner
        self.compiler = compiler
        self.motion_planner = motion_planner
        self.last_trace: list[tuple[str, object, object]] = []

    def solve(self, request: PlanningRequest) -> ExecutableProposal | Failure:
        """中文: solve 在同一墙钟预算内重编译联合草稿并生成运动候选, 避免失败或迟到结果进入后续阶段.

        English: solve recompiles a joint draft and prepares motion under one wall-clock budget so failed or late results cannot advance.
        Runtime must separately validate and atomically commit the candidate. Synchronous stages
        cannot be preempted here; expired results are discarded. Inputs remain read-only.
        """
        started = monotonic()
        self.last_trace = []
        failure = validate_request(request)
        if failure is not None:
            return failure
        assignment = request.assignment
        deadline = started + assignment.budget_s
        timeout = Failure("TIMEOUT", "Shared planning budget exhausted", (assignment.start.request_id,))
        remaining = deadline - monotonic()
        if remaining <= 0:
            return timeout
        joint_request = replace(assignment, budget_s=remaining)
        candidate = self.joint_planner.plan(joint_request)
        self.last_trace.append(("joint", joint_request, candidate))
        if isinstance(candidate, Failure):
            return candidate
        if monotonic() >= deadline:
            return timeout
        jobs = self.compiler.compile_jobs(assignment, candidate.task_delta)
        self.last_trace.append(("compilation", (assignment, candidate.task_delta), jobs))
        if isinstance(jobs, Failure):
            return jobs
        failure = validate_plan(request, jobs, candidate.plan)
        if failure is not None:
            return failure
        remaining = deadline - monotonic()
        if remaining <= 0:
            return timeout
        motion_request = MotionRequest(
            assignment.start, jobs, candidate.plan, request.target_end_s, remaining,
        )
        motion = self.motion_planner.prepare(motion_request)
        self.last_trace.append(("tpg", motion_request, motion))
        if isinstance(motion, Failure):
            return motion
        if monotonic() >= deadline:
            return timeout
        return ExecutableProposal(assignment.start.request_id, candidate.task_delta, motion)
