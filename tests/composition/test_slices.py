"""中文: 本模块从独立边界输入验证真实模块组合, 防止测试只核对调用顺序.

English: This module tests real compositions from independent boundary inputs instead of checking only call order.
"""
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import unittest

from warehouse_api.contracts import Failure, Move, Pose2, Twist2
from .replay import STAGES, boundary_case, run_slice


class CompositionTests(unittest.TestCase):
    """中文: CompositionTests 验证不需要二进制的组合与失败停止, 保持日常检查可运行.

    English: CompositionTests verifies non-native compositions and failure stops so daily checks remain runnable.
    """

    def test_allocation_and_compilation_outputs_match_independent_requirements(self):
        """中文: 本测试检查分配到编译的三种组合, 确认需求变化产生正确任务和物理动作.

        English: This test checks three allocation/compiler slices so demand changes produce correct tasks and physical actions.
        """
        for quantity, station, destination in ((1, 3, 5), (3, 4, 8)):
            model, inputs, expected = boundary_case(quantity, station, destination)
            for first, last in ((0, 0), (0, 1), (1, 1)):
                with self.subTest(quantity=quantity, first=first, last=last):
                    before = copy.deepcopy((model, inputs[first]))
                    evidence = run_slice(model, first, last, inputs[first])
                    self.assertEqual(evidence['result'], expected[last])
                    self.assertEqual((model, inputs[first]), before)
                    self.assertEqual([row[0] for row in evidence['trace']], list(STAGES[first:last+1]))
                    self.assertEqual(evidence['native_evidence'], {})

    def test_each_boundary_rejects_bad_input_without_native_work(self):
        """中文: 本测试在四个入口注入不同失败, 确认失败原因保留且后续阶段不运行.

        English: This test injects failures at all four entries so diagnostics survive and later stages never run.
        """
        model, inputs, _ = boundary_case()
        assignment, draft = inputs[1]
        cases = (
            (0, replace(assignment, stock=(replace(assignment.stock[0], available_quantity=0),)), 'NO_PLAN'),
            (1, (assignment, replace(draft, queues=())), 'BAD_INPUT'),
            (2, replace(inputs[2], jobs=()), 'UNSUPPORTED'),
            (3, replace(inputs[3], fleet_plan=replace(inputs[3].fleet_plan, request_id='stale')), 'STALE_REQUEST'),
        )
        for first, request, code in cases:
            with self.subTest(first=first):
                before = copy.deepcopy(request)
                evidence = run_slice(model, first, 3, request, Path('/nonexistent-binaries'))
                self.assertIsInstance(evidence['result'], Failure)
                self.assertEqual(evidence['result'].code, code)
                self.assertTrue(evidence['result'].message)
                self.assertEqual(len(evidence['trace']), 1)
                self.assertEqual(evidence['native_evidence'], {})
                self.assertEqual(request, before)

    def test_bad_route_geometry_is_rejected_at_motion_input(self):
        """中文: 本测试改变路线第一条边, 确认 TPG 检查真实到达关系而不只接受动作名称.

        English: This test changes the first edge so TPG must check actual reachability, not only action names.
        """
        model, inputs, _ = boundary_case()
        motion = inputs[3]
        route = motion.fleet_plan.routes[0]
        broken = replace(route, steps=(Move('e1'),) + route.steps[1:])
        request = replace(motion, fleet_plan=replace(motion.fleet_plan, routes=(broken,)))
        evidence = run_slice(model, 3, 3, request, Path('/nonexistent-binaries'))
        self.assertEqual(evidence['result'].code, 'BAD_INPUT')
        self.assertEqual(evidence['native_evidence'], {})


@unittest.skipUnless(os.environ.get('WAREHOUSE_NATIVE_BIN'), 'set WAREHOUSE_NATIVE_BIN for native slices')
class NativeCompositionTests(unittest.TestCase):
    """中文: NativeCompositionTests 检查七种含原生程序的组合, 使每个边界有独立业务断言.

    English: NativeCompositionTests checks seven native slices so each boundary has independent functional assertions.
    """

    def test_native_matrix_preserves_routes_action_locations_and_holds(self):
        """中文: 本测试核对路线, 动作位置, 完整静止耗时和停车拼接, 防止固定输出冒充组合功能.

        English: This test checks routes, action locations, full stationary holds and stop splices so canned output cannot stand in for composition behavior.
        """
        for quantity, station, destination in ((1, 3, 5), (3, 4, 8)):
            model, inputs, expected = boundary_case(quantity, station, destination)
            for first in range(4):
                for last in range(max(first, 2), 4):
                    with self.subTest(quantity=quantity, first=first, last=last):
                        before = copy.deepcopy((model, inputs[first]))
                        evidence = run_slice(model, first, last, inputs[first], Path(os.environ['WAREHOUSE_NATIVE_BIN']))
                        result = evidence['result']
                        self.assertNotIsInstance(result, Failure)
                        self.assertEqual((model, inputs[first]), before)
                        self.assertEqual([row[0] for row in evidence['trace']], list(STAGES[first:last+1]))
                        for stage in STAGES[max(first, 2):last+1]:
                            records = [json.loads(value) for name, value in evidence['native_evidence'][stage].items()
                                       if name.endswith('.run.json')]
                            self.assertEqual(len(records), 3)
                            self.assertTrue(all(row['exit_code'] == 0 and not row['timed_out'] for row in records))
                        if last == 2:
                            self.assertEqual(result, expected[2])
                            continue
                        segment = result.common_prefix[0]
                        self.assertEqual(segment.robot_id, 'A')
                        self.assertEqual(segment.knots[0].pose, Pose2(0, 0, 0))
                        self.assertEqual([a.step for a in segment.actions], [a.step for a in expected[1][0].actions])
                        self.assertEqual(segment.knots[-1].pose, Pose2(destination, 0, 0))
                        self.assertEqual(segment.knots[-1].velocity, Twist2(0, 0, 0))
                        self.assertEqual(result.stop_tail[0].knots[0], segment.knots[-1])
                        for scheduled, action, x in zip(segment.actions, expected[1][0].actions, (1, station, destination)):
                            self.assertAlmostEqual(scheduled.start_s / .1, round(scheduled.start_s / .1))
                            holds = [(a, b) for a, b in zip(segment.knots, segment.knots[1:])
                                     if abs(a.time_s - scheduled.start_s) < 1e-8]
                            self.assertEqual(len(holds), 1)
                            left, right = holds[0]
                            self.assertAlmostEqual(right.time_s - left.time_s, action.duration_s)
                            self.assertEqual(left.pose, Pose2(x, 0, 0))
                            self.assertEqual(right.pose, left.pose)
                            self.assertEqual((left.velocity, right.velocity), (Twist2(0, 0, 0),) * 2)
