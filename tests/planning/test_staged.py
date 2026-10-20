"""Trace stage boundaries, failures, deadlines, and candidate immutability."""
import copy
from dataclasses import replace
from itertools import chain, count, repeat
import unittest
from unittest.mock import Mock, patch

from .replay import scenario
from warehouse_api.contracts import ExecutableProposal, Failure, SharedCompiler
from warehouse_api.serialization import dumps, loads


# 中文: StagedPipelineTests 测试类检查阶段连接, 时间预算和失败传播, 单独定位编排错误. 这些测试防止缺少必要阶段结果或已失败的候选继续进入下游.
# English: StagedPipelineTests tests stage wiring, budgets and failure propagation independently of native algorithms so
# partial or failed candidates cannot continue downstream.
class StagedPipelineTests(unittest.TestCase):
    # 中文: setUp 方法为每个用例建立独立流水线和阶段输入输出记录 trace, 防止替身 mock 的调用历史或候选状态影响其他断言.
    # English: setUp creates an independent pipeline and stage-I/O trace per test so test-double call history and candidate state
    # cannot contaminate other assertions.
    def setUp(self):
        self.model, self.request, self.pipeline, self.trace = scenario()

    # 中文: 本测试用预设求解器输出的 fixture 链检查阶段顺序, 动作耗时和输入不变. 这些断言保护模块间的数据传递, 不证明原生集成已完成.
    # English: This test checks stage order with preset solver outputs, action timing and input immutability to protect interface
    # propagation without treating fixtures as native integration evidence.
    def test_full_fixture_chain_preserves_actions_and_snapshots(self):
        before = copy.deepcopy((self.model, self.request))
        result = self.pipeline.solve(self.request)
        self.assertIsInstance(result, ExecutableProposal)
        self.assertEqual([row["stage"] for row in self.trace],
                         ["orders", "allocation", "compile", "mapf", "tpg"])
        jobs = self.trace[2]["output"]
        motion_request = self.trace[4]["input"]
        self.assertIs(motion_request.jobs, jobs)
        self.assertIs(motion_request.start, self.request.assignment.start)
        self.assertEqual([a.kind for a in jobs[0].actions], ["lift", "serve", "drop"])
        self.assertEqual([a.duration_s for a in jobs[0].actions], [0.3, 0.3, 0.3])
        self.assertEqual([a.step for a in result.motion.common_prefix[0].actions],
                         [a.step for a in jobs[0].actions])
        self.assertEqual((self.model, self.request), before)
        self.assertEqual(loads(ExecutableProposal, dumps(result)), result)
        self.assertEqual(self.pipeline.solve(self.request), result)

    # 中文: 本测试逐阶段注入带原因的失败结果 Failure 并检查后续未调用, 保证失败原因原样传播, 防止在无效输入上继续求解.
    # English: This test injects a Failure result carrying diagnostics at each stage and checks downstream calls stop so diagnostics survive
    # and invalid results cannot trigger further solving.
    def test_each_failure_stops_downstream_calls_and_preserves_diagnostics(self):
        for failed_stage in range(4):
            with self.subTest(stage=failed_stage):
                _, request, pipeline, _ = scenario()
                pipeline.compiler = Mock(spec=SharedCompiler, wraps=pipeline.compiler)
                calls = [pipeline.allocator.allocate, pipeline.compiler.compile_jobs,
                         pipeline.path_planner.plan, pipeline.motion_planner.prepare]
                failure = Failure("UNSUPPORTED", "deliberate stage rejection", ("shelf",))
                # 中文: 替身回调忽略入参并返回指定失败, 单独检验编排的停止与传播行为.
                # English: The test-double callback returns the injected failure for any arguments to isolate orchestration stop behavior.
                calls[failed_stage].side_effect = lambda *args: failure
                self.assertIs(pipeline.solve(request), failure)
                for call in calls[failed_stage + 1:]:
                    call.assert_not_called()

    # 中文: 本测试制造编译层拒绝的草稿, 检查路径与运动阶段未启动, 保护共享语义检查的门禁作用.
    # English: This test uses a compiler-rejected draft to check that path and motion stages never start,
    # preserving compilation as a semantic boundary.
    def test_compiler_rejection_blocks_native_boundaries(self):
        draft = self.pipeline.allocator.allocate(self.request.assignment)
        self.pipeline.allocator.allocate.side_effect = None
        self.pipeline.allocator.allocate.return_value = replace(draft, queues=())
        result = self.pipeline.solve(self.request)
        self.assertEqual(result.code, "BAD_INPUT")
        self.pipeline.path_planner.plan.assert_not_called()
        self.pipeline.motion_planner.prepare.assert_not_called()

    # 中文: 本测试使用递增时钟核对阶段剩余预算, 防止各求解器重新获得完整预算, 让总规划时间有共同上限.
    # English: This test uses an increasing clock to check remaining stage budgets so each solver cannot
    # restart the full planning allowance.
    def test_shared_budget_decreases_across_stages(self):
        with patch("warehouse_api.planning._staged.monotonic", side_effect=count()):
            result = self.pipeline.solve(self.request)
        self.assertIsInstance(result, ExecutableProposal)
        self.assertEqual(self.trace[1]["input"].budget_s, 9)
        self.assertEqual(self.trace[3]["input"].budget_s, 7)
        self.assertEqual(self.trace[4]["input"].budget_s, 6)
        self.assertEqual(self.request.assignment.budget_s, 10)

    # 中文: 本测试在每个阶段边界模拟超时, 验证流水线及时停止并丢弃迟到结果. 时钟替身持续返回到期时间, 避免有限迭代器耗尽后干扰断言.
    # English: This test expires the clock at each boundary with an unbounded expired tail so stopping and
    # late-result rejection are tested without iterator exhaustion.
    def test_deadline_before_each_stage_and_after_motion(self):
        for expired_call in range(1, 6):
            with self.subTest(expired_call=expired_call):
                _, request, pipeline, trace = scenario()
                times = chain(repeat(0, expired_call), repeat(10))
                with patch("warehouse_api.planning._staged.monotonic", side_effect=times):
                    result = pipeline.solve(request)
                self.assertEqual(result.code, "TIMEOUT")
                self.assertEqual(len(trace), [1, 2, 2, 4, 5][expired_call - 1])

    # 中文: 本测试让路径返回旧请求 ID, 确认轨迹生成阶段 TPG 不会使用过期路线, 防止不同轮规划的数据混接.
    # English: This test returns an old request ID from routing and checks trajectory generation is blocked so results from
    # different planning rounds cannot be mixed.
    def test_stale_path_result_stops_motion(self):
        self.pipeline.solve(self.request)
        plan = self.trace[3]["output"]
        self.pipeline.path_planner.plan.side_effect = None
        self.pipeline.path_planner.plan.return_value = replace(plan, request_id="old")
        self.pipeline.motion_planner.reset_mock()
        self.assertEqual(self.pipeline.solve(self.request).code, "STALE_REQUEST")
        self.pipeline.motion_planner.prepare.assert_not_called()

    # 中文: 本测试在入口提交非法预算或目标时间, 检查分配器未运行, 避免明知无效的请求消耗求解资源.
    # English: This test submits invalid budgets or horizons and checks allocation never starts so malformed
    # requests consume no solving resources.
    def test_bad_budget_and_target_do_not_start_allocation(self):
        for budget in (0, -1, float("nan"), float("inf")):
            request = replace(self.request, assignment=replace(self.request.assignment, budget_s=budget))
            self.assertEqual(self.pipeline.solve(request).code, "BAD_INPUT")
        for target in (0, -1, float("nan"), float("inf")):
            self.assertEqual(self.pipeline.solve(replace(self.request, target_end_s=target)).code,
                             "BAD_INPUT")
        self.pipeline.allocator.allocate.assert_not_called()

    # 中文: 本测试在请求 ID 正确时替换机器人或动作序列, 验证仍拒绝并停止轨迹生成阶段 TPG, 防止仅凭请求标签信任错误路线.
    # English: This test alters robot coverage or action order under a valid request ID so identity alone
    # cannot make a mismatched route reach the TPG trajectory-generation stage.
    def test_matching_request_id_does_not_hide_wrong_jobs(self):
        self.pipeline.solve(self.request)
        plan = self.trace[3]["output"]
        route = plan.routes[0]
        for routes in ((), (route, route), (replace(route, robot_id="unknown"),),
                       (replace(route, steps=()),),
                       (replace(route, steps=tuple(reversed(route.steps))),)):
            with self.subTest(routes=routes):
                self.pipeline.path_planner.plan.side_effect = None
                self.pipeline.path_planner.plan.return_value = replace(plan, routes=routes)
                self.pipeline.motion_planner.reset_mock()
                self.assertEqual(self.pipeline.solve(self.request).code, "BAD_INPUT")
                self.pipeline.motion_planner.prepare.assert_not_called()

    # 中文: 本测试让适配器抛出开发错误, 检查异常原样传播且后续停止, 防止宽泛容错掩盖实现缺陷.
    # English: This test raises a programming error in an adapter and checks it propagates while later stages
    # stop so broad recovery cannot hide implementation defects.
    def test_stage_exceptions_keep_original_traceback(self):
        self.pipeline.allocator.allocate.side_effect = ValueError("adapter bug")
        with self.assertRaisesRegex(ValueError, "adapter bug"):
            self.pipeline.solve(self.request)
        self.pipeline.path_planner.plan.assert_not_called()
