"""Trace stage boundaries, failures, deadlines, and candidate immutability."""
import copy
from dataclasses import replace
from itertools import count
import unittest
from unittest.mock import Mock, patch

from .replay import scenario
from warehouse_api.contracts import ExecutableProposal, Failure, SharedCompiler
from warehouse_api.serialization import dumps, loads


class StagedPipelineTests(unittest.TestCase):
    def setUp(self):
        self.model, self.request, self.pipeline, self.trace = scenario()

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

    def test_each_failure_stops_downstream_calls_and_preserves_diagnostics(self):
        for failed_stage in range(4):
            with self.subTest(stage=failed_stage):
                _, request, pipeline, _ = scenario()
                pipeline.compiler = Mock(spec=SharedCompiler, wraps=pipeline.compiler)
                calls = [pipeline.allocator.allocate, pipeline.compiler.compile_jobs,
                         pipeline.path_planner.plan, pipeline.motion_planner.prepare]
                failure = Failure("UNSUPPORTED", "deliberate stage rejection", ("shelf",))
                calls[failed_stage].side_effect = lambda *args: failure
                self.assertIs(pipeline.solve(request), failure)
                for call in calls[failed_stage + 1:]:
                    call.assert_not_called()

    def test_compiler_rejection_blocks_native_boundaries(self):
        draft = self.pipeline.allocator.allocate(self.request.assignment)
        self.pipeline.allocator.allocate.side_effect = None
        self.pipeline.allocator.allocate.return_value = replace(draft, queues=())
        result = self.pipeline.solve(self.request)
        self.assertEqual(result.code, "BAD_INPUT")
        self.pipeline.path_planner.plan.assert_not_called()
        self.pipeline.motion_planner.prepare.assert_not_called()

    def test_shared_budget_decreases_across_stages(self):
        with patch("warehouse_api.planning._staged.monotonic", side_effect=count()):
            result = self.pipeline.solve(self.request)
        self.assertIsInstance(result, ExecutableProposal)
        self.assertEqual(self.trace[1]["input"].budget_s, 9)
        self.assertEqual(self.trace[3]["input"].budget_s, 7)
        self.assertEqual(self.trace[4]["input"].budget_s, 6)
        self.assertEqual(self.request.assignment.budget_s, 10)

    def test_deadline_before_each_stage_and_after_motion(self):
        for expired_call in range(1, 6):
            with self.subTest(expired_call=expired_call):
                _, request, pipeline, trace = scenario()
                times = [0] * expired_call + [10]
                with patch("warehouse_api.planning._staged.monotonic", side_effect=times):
                    result = pipeline.solve(request)
                self.assertEqual(result.code, "TIMEOUT")
                self.assertEqual(len(trace), [1, 2, 2, 4, 5][expired_call - 1])

    def test_stale_path_result_stops_motion(self):
        self.pipeline.solve(self.request)
        plan = self.trace[3]["output"]
        self.pipeline.path_planner.plan.side_effect = None
        self.pipeline.path_planner.plan.return_value = replace(plan, request_id="old")
        self.pipeline.motion_planner.reset_mock()
        self.assertEqual(self.pipeline.solve(self.request).code, "STALE_REQUEST")
        self.pipeline.motion_planner.prepare.assert_not_called()

    def test_bad_budget_and_target_do_not_start_allocation(self):
        for budget in (0, -1, float("nan"), float("inf")):
            request = replace(self.request, assignment=replace(self.request.assignment, budget_s=budget))
            self.assertEqual(self.pipeline.solve(request).code, "BAD_INPUT")
        for target in (0, -1, float("nan"), float("inf")):
            self.assertEqual(self.pipeline.solve(replace(self.request, target_end_s=target)).code,
                             "BAD_INPUT")
        self.pipeline.allocator.allocate.assert_not_called()

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

    def test_stage_exceptions_keep_original_traceback(self):
        self.pipeline.allocator.allocate.side_effect = ValueError("adapter bug")
        with self.assertRaisesRegex(ValueError, "adapter bug"):
            self.pipeline.solve(self.request)
        self.pipeline.path_planner.plan.assert_not_called()
