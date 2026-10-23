"""Joint composition tests use explicit solver doubles, not native TAPF evidence."""
import copy
from dataclasses import replace
from itertools import repeat, chain
import unittest
from unittest.mock import Mock, patch

from .replay import scenario
from warehouse_api.contracts import (
    ExecutableProposal, Failure, JointPlan, JointPlanner, SharedCompiler,
)
from warehouse_api.planning import JointPipeline
from warehouse_api.serialization import dumps, loads


class JointPipelineTests(unittest.TestCase):
    """中文: JointPipelineTests 检查联合候选的语义门禁, 防止错误草稿进入运动规划.

    English: JointPipelineTests checks semantic gates so invalid joint drafts cannot reach motion planning.
    """

    def setUp(self):
        """中文: setUp 用真实编译器和显式替身准备候选, 隔离编排行为.

        English: setUp prepares a real compiler and explicit doubles to isolate orchestration behavior.
        """
        self.model, self.request, staged, trace = scenario()
        staged.solve(self.request)
        self.candidate = JointPlan(trace[1]["output"], trace[3]["output"])
        self.joint = Mock(spec=JointPlanner)
        self.joint.plan.return_value = self.candidate
        self.compiler = Mock(spec=SharedCompiler, wraps=staged.compiler)
        self.motion = staged.motion_planner
        self.motion.reset_mock()
        self.pipeline = JointPipeline(self.joint, self.compiler, self.motion)

    def test_complete_candidate_uses_shared_compilation_without_mutating_input(self):
        """中文: 本测试验证草稿重新编译和输入不变, 避免联合求解绕过共享动作语义.

        English: This test verifies draft recompilation and unchanged input so joint search cannot bypass shared action semantics.
        """
        before = copy.deepcopy((self.model, self.request, self.candidate))
        result = self.pipeline.solve(self.request)
        self.assertIsInstance(result, ExecutableProposal)
        self.assertIs(result.task_delta, self.candidate.task_delta)
        self.compiler.compile_jobs.assert_called_once_with(self.request.assignment, self.candidate.task_delta)
        motion_request = self.motion.prepare.call_args.args[0]
        self.assertIs(motion_request.fleet_plan, self.candidate.plan)
        self.assertEqual([a.kind for a in motion_request.jobs[0].actions], ["lift", "serve", "drop"])
        self.assertEqual((self.model, self.request, self.candidate), before)
        self.assertEqual(loads(JointPlan, dumps(self.candidate)), self.candidate)
        self.assertEqual([row[0] for row in self.pipeline.last_trace], ["joint", "compilation", "tpg"])

    def test_rejected_draft_and_mismatched_routes_block_motion(self):
        """中文: 本测试破坏队列和路线引用, 确认联合结果不能靠请求 ID 绕过检查.

        English: This test corrupts queues and route references so request identity cannot bypass validation.
        """
        plan = self.candidate.plan
        route = plan.routes[0]
        cases = [
            (replace(self.candidate, task_delta=replace(self.candidate.task_delta, queues=())), "BAD_INPUT"),
            (replace(self.candidate, plan=replace(plan, request_id="old")), "STALE_REQUEST"),
            (replace(self.candidate, plan=replace(plan, routes=())), "BAD_INPUT"),
            (replace(self.candidate, plan=replace(plan, routes=(route, route))), "BAD_INPUT"),
            (replace(self.candidate, plan=replace(plan, routes=(replace(route, steps=()),))), "BAD_INPUT"),
        ]
        for candidate, code in cases:
            with self.subTest(code=code, candidate=candidate):
                self.joint.plan.return_value = candidate
                self.assertEqual(self.pipeline.solve(self.request).code, code)
                self.motion.prepare.assert_not_called()

    def test_failure_propagation_and_trace_reset(self):
        """中文: 本测试在各阶段注入失败, 保留诊断并阻止下游继续计算.

        English: This test injects stage failures to preserve diagnostics and prevent downstream work.
        """
        failure = Failure("UNSUPPORTED", "unsupported warehouse action", ("shelf",))
        self.pipeline.solve(self.request)
        self.joint.plan.return_value = failure
        self.compiler.reset_mock()
        self.motion.reset_mock()
        self.assertIs(self.pipeline.solve(self.request), failure)
        self.compiler.compile_jobs.assert_not_called()
        self.motion.prepare.assert_not_called()
        self.assertEqual(len(self.pipeline.last_trace), 1)
        self.joint.plan.return_value = self.candidate
        self.compiler.compile_jobs.side_effect = None
        self.compiler.compile_jobs.return_value = failure
        self.assertIs(self.pipeline.solve(self.request), failure)
        self.motion.prepare.assert_not_called()

    def test_motion_failure_and_programming_errors_propagate(self):
        """中文: 本测试保留运动失败和原始异常, 防止编排隐藏开发错误.

        English: This test preserves motion failures and original exceptions so orchestration cannot hide programming errors.
        """
        failure = Failure("UNSUPPORTED", "unsupported motion", ())
        self.motion.prepare.side_effect = None
        self.motion.prepare.return_value = failure
        self.assertIs(self.pipeline.solve(self.request), failure)
        self.joint.plan.side_effect = ValueError("joint adapter bug")
        self.motion.reset_mock()
        with self.assertRaisesRegex(ValueError, "joint adapter bug"):
            self.pipeline.solve(self.request)
        self.motion.prepare.assert_not_called()

    def test_shared_budget_and_late_results(self):
        """中文: 本测试控制时钟, 确认联合计算与运动规划共用预算且迟到结果被丢弃.

        English: This test controls time so joint and motion planning share a budget and late results are discarded.
        """
        with patch("warehouse_api.planning._joint.monotonic", side_effect=[0, 1, 2, 3, 4]):
            self.assertIsInstance(self.pipeline.solve(self.request), ExecutableProposal)
        self.assertEqual(self.joint.plan.call_args.args[0].budget_s, 9)
        self.assertEqual(self.motion.prepare.call_args.args[0].budget_s, 7)
        for boundary in range(1, 5):
            with self.subTest(boundary=boundary):
                self.compiler.reset_mock()
                self.motion.reset_mock()
                with patch("warehouse_api.planning._joint.monotonic",
                           side_effect=chain(repeat(0, boundary), repeat(10))):
                    self.assertEqual(self.pipeline.solve(self.request).code, "TIMEOUT")
                if boundary <= 2:
                    self.compiler.compile_jobs.assert_not_called()
                if boundary <= 3:
                    self.motion.prepare.assert_not_called()

    def test_invalid_request_never_starts_joint_search(self):
        """中文: 本测试拒绝非法时间输入, 防止无效请求消耗联合搜索资源.

        English: This test rejects invalid timing input so malformed requests consume no joint search resources.
        """
        for budget in (0, -1, float("nan"), float("inf")):
            request = replace(self.request, assignment=replace(self.request.assignment, budget_s=budget))
            self.assertEqual(self.pipeline.solve(request).code, "BAD_INPUT")
        self.assertEqual(self.pipeline.solve(replace(self.request, target_end_s=0)).code, "BAD_INPUT")
        self.joint.plan.assert_not_called()
