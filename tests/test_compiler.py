"""Current-task compilation and explicit rejection traces; no solver execution."""
import copy
from dataclasses import replace
import unittest

from warehouse_api.codec import dumps, loads
from warehouse_api.compiler import CurrentTaskCompiler
from warehouse_api.contracts import (
    ActionTimes, AssignmentRequest, Drop, Failure, Lift, MotionLimits, Node,
    ObjectSpec, ObjectState, PhysicalAction, PhysicalState, Pick, Place,
    PlanningStart, Point2, Polygon, Pose2, QueueState, Resource, RobotJobs,
    RobotQueue, RobotSpec, RobotState, RunningAction, Serve, SharedCompiler,
    StepLock, StepRef, Task, TaskDelta, TaskProgress, Twist2, WorldModel,
)


def fixture():
    shape = Polygon((Point2(0, 0), Point2(1, 0), Point2(0, 1)))
    model = WorldModel(
        "compiler-fixture", (Node("home-node", Point2(0, 0)),
                             Node("station-node", Point2(2, 0)),
                             Node("return-node", Point2(4, 0))), (), (),
        tuple(Resource(name, shape, 1) for name in ("home", "station", "return")),
        tuple(RobotSpec(name, shape) for name in ("A", "B")),
        (ObjectSpec("shelf", shape, Pose2(0, 0, 0), True),),
        (Place("home", "storage", "home-node", 0, "home"),
         Place("station", "station", "station-node", 1.5, "station"),
         Place("return", "storage", "return-node", 0, "return")),
        MotionLimits(1, 1, 1, 1, 2, 3), ActionTimes(0.21, 0.3, 0.1, 0.2),
    )
    task = Task("T", (Lift("shelf"), Serve("station", (Pick("O", "X", 1),)), Drop("return")))
    state = PhysicalState(
        10, tuple(RobotState(name, Pose2(0, 0, 0), Twist2(0, 0, 0)) for name in ("A", "B")),
        (ObjectState("shelf", Pose2(0, 0, 0), None),), (),
    )
    request = AssignmentRequest(PlanningStart("request", 1, 9, state, (), 11), (), (),
                                (TaskProgress(task, 0, False),), (QueueState("A", ("T",), 1),), (), 1)
    return model, request


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.model, self.request = fixture()
        self.compiler: SharedCompiler = CurrentTaskCompiler(self.model, sim_dt_s=0.1)
        self.draft = TaskDelta((), ())

    def compile(self, **changes):
        return self.compiler.compile_jobs(replace(self.request, **changes), self.draft)

    def state(self, **changes):
        return replace(self.request.start, join_state=replace(self.request.start.join_state, **changes))

    def progress(self, index, **changes):
        return (replace(self.request.tasks[0], next_step=index, **changes),)

    def assert_failure(self, result, code):
        self.assertIsInstance(result, Failure)
        self.assertEqual(result.code, code)
        self.assertTrue(result.message)

    def test_full_actions_and_idle_robot(self):
        expected = tuple(PhysicalAction(StepRef("T", i), kind, "shelf", node, yaw, 0.3, (resource,))
                         for i, (kind, node, yaw, resource) in enumerate((
                             ("lift", "home-node", 0, "home"),
                             ("serve", "station-node", 1.5, "station"),
                             ("drop", "return-node", 0, "return"))))
        self.assertEqual(self.compile(), (RobotJobs("A", expected), RobotJobs("B", ())))

    def test_projected_progress_is_not_advanced_again(self):
        carried = self.state(objects=(ObjectState("shelf", None, "A"),))
        for index in (1, 2):
            with self.subTest(next_step=index):
                result = self.compile(start=carried, tasks=self.progress(index))
                self.assertEqual([a.step.step_index for a in result[0].actions], list(range(index, 3)))
                self.assertTrue(all(a.object_id == "shelf" for a in result[0].actions))
        self.assertEqual(self.compile(tasks=self.progress(3)), (RobotJobs("A", ()), RobotJobs("B", ())))

    def test_empty_delta_keeps_binding_and_empty_queues_leave_unstarted_task_unbound(self):
        self.assertEqual(len(self.compile()[0].actions), 3)
        self.assertEqual(self.compile(queues=()), (RobotJobs("A", ()), RobotJobs("B", ())))

    def test_action_lock_preserves_executor_even_with_zero_locked_prefix(self):
        lock = (StepLock(StepRef("T", 0), "A"),)
        self.assertIsInstance(self.compile(locks=lock, queues=(QueueState("A", ("T",), 0),)), tuple)
        for queues in ((), (QueueState("B", ("T",), 0),)):
            self.assert_failure(self.compile(locks=lock, queues=queues), "CONFLICT")
        for ref in (StepRef("missing", 0), StepRef("T", -1), StepRef("T", 3)):
            self.assert_failure(self.compile(locks=(StepLock(ref, "A"),)), "BAD_INPUT")

    def test_carry_ownership_and_orphaned_carry(self):
        for carrier in (None, "B"):
            obj = ObjectState("shelf", Pose2(0, 0, 0) if carrier is None else None, carrier)
            self.assert_failure(self.compile(start=self.state(objects=(obj,)), tasks=self.progress(1)), "CONFLICT")
        carried = self.state(objects=(ObjectState("shelf", None, "A"),))
        for changes in ({}, {"queues": ()}, {"tasks": self.progress(3)}):
            self.assert_failure(self.compile(start=carried, **changes), "CONFLICT")
        self.assert_failure(self.compile(tasks=self.progress(1), queues=()), "CONFLICT")

    def test_blocked_current_task_does_not_retry(self):
        self.assert_failure(self.compile(tasks=self.progress(0, blocked=True)), "NO_PLAN")

    def test_lift_preconditions_preserve_diagnostics_and_inputs(self):
        other = replace(self.model.objects[0], id="other-shelf")
        model = replace(self.model, objects=self.model.objects + (other,))
        compiler = CurrentTaskCompiler(model, sim_dt_s=0.1)
        cases = (
            (ObjectState("shelf", None, "B"), ObjectState("other-shelf", Pose2(4, 0, 0), None)),
            (ObjectState("shelf", Pose2(0, 0, 0), None), ObjectState("other-shelf", None, "A")),
        )
        for objects in cases:
            with self.subTest(objects=objects):
                request = replace(self.request, start=self.state(objects=objects))
                original = copy.deepcopy((model, request, self.draft))
                result = compiler.compile_jobs(request, self.draft)
                self.assertEqual(result, Failure(
                    "CONFLICT", "Lift requires an empty robot and grounded shelf", ("A", "shelf"),
                ))
                self.assertEqual((model, request, self.draft), original)

    def test_queue_edits_and_new_definitions_are_explicitly_deferred(self):
        for draft in (TaskDelta((self.request.tasks[0].task,), ()),
                      TaskDelta((), (RobotQueue("A", ()),))):
            self.assert_failure(self.compiler.compile_jobs(self.request, draft), "UNSUPPORTED")
        self.assert_failure(self.compile(queues=(QueueState("A", ("T", "T"), 0),)), "UNSUPPORTED")

    def test_running_action_at_splice_is_rejected(self):
        start = self.state(running_actions=(RunningAction("A", StepRef("T", 0), 9, 11),))
        self.assert_failure(self.compile(start=start), "UNSUPPORTED")

    def test_progress_binding_and_duplicate_id_errors(self):
        for index in (-1, 4):
            self.assert_failure(self.compile(tasks=self.progress(index)), "BAD_INPUT")
        for queues in ((QueueState("A", ("T",), 2),), (QueueState("unknown", (), 0),),
                       (QueueState("A", ("missing",), 0),), self.request.queues * 2,
                       (QueueState("A", ("T",), 0), QueueState("B", ("T",), 0))):
            self.assert_failure(self.compile(queues=queues), "BAD_INPUT")
        self.assert_failure(self.compile(tasks=self.request.tasks * 2), "BAD_INPUT")

    def test_incomplete_and_inconsistent_physical_state(self):
        state = self.request.start.join_state
        for changes in ({"robots": state.robots[:1]}, {"robots": state.robots * 2},
                        {"objects": ()}, {"objects": state.objects * 2},
                        {"objects": (ObjectState("shelf", None, None),)},
                        {"objects": (ObjectState("shelf", Pose2(0, 0, 0), "A"),)},
                        {"objects": (ObjectState("shelf", None, "unknown"),)}):
            self.assert_failure(self.compile(start=self.state(**changes)), "BAD_INPUT")

    def test_duplicate_shelf_claims(self):
        task = replace(self.request.tasks[0].task, id="T2")
        self.assert_failure(self.compile(tasks=self.request.tasks + (TaskProgress(task, 0, False),),
                                        queues=self.request.queues + (QueueState("B", ("T2",), 0),)), "CONFLICT")

    def test_unsupported_task_shape_offset_and_pickup_pose(self):
        task = replace(self.request.tasks[0].task, steps=(Drop("return"),))
        self.assert_failure(self.compile(tasks=self.progress(0, task=task)), "UNSUPPORTED")
        self.assert_failure(self.compile(start=self.state(objects=(ObjectState("shelf", Pose2(0.01, 0, 0), None),))), "UNSUPPORTED")
        for model in (replace(self.model, objects=(replace(self.model.objects[0], carry_offset=Pose2(1, 0, 0)),)),
                      replace(self.model, places=self.model.places + (replace(self.model.places[0], id="alias"),))):
            compiler = CurrentTaskCompiler(model, sim_dt_s=0.1)
            self.assert_failure(compiler.compile_jobs(self.request, self.draft), "UNSUPPORTED")

    def test_unknown_shelf_and_wrong_place_kind(self):
        for index, action in ((0, Lift("missing")), (1, Serve("home", (Pick("O", "X", 1),))),
                              (2, Drop("station")), (2, Drop("missing"))):
            steps = list(self.request.tasks[0].task.steps)
            steps[index] = action
            task = replace(self.request.tasks[0].task, steps=tuple(steps))
            self.assert_failure(self.compile(tasks=self.progress(0, task=task)), "BAD_INPUT")

    def test_shape_and_configuration_errors_keep_original_exceptions(self):
        with self.assertRaises(ValueError):
            CurrentTaskCompiler(self.model, sim_dt_s=0)
        for model in (replace(self.model, robots=self.model.robots * 2),
                      replace(self.model, nodes=self.model.nodes * 2),
                      replace(self.model, resources=self.model.resources * 2),
                      replace(self.model, objects=self.model.objects * 2),
                      replace(self.model, places=self.model.places * 2),
                      replace(self.model, places=(replace(self.model.places[0], node_id="missing"),)),
                      replace(self.model, places=(replace(self.model.places[0], resource_id="missing"),))):
            with self.assertRaises(ValueError):
                CurrentTaskCompiler(model, sim_dt_s=0.1)
        with self.assertRaises(ValueError):
            self.compile(tasks=self.progress(True))

    def test_repeat_and_json_replay_leave_all_inputs_unchanged(self):
        original = copy.deepcopy((self.model, self.request, self.draft))
        expected = self.compile()
        replay = loads(AssignmentRequest, dumps(self.request))
        self.assertEqual(self.compiler.compile_jobs(replay, self.draft), expected)
        self.assertEqual(self.compile(), expected)
        self.assertEqual((self.model, self.request, self.draft), original)
        self.assert_failure(self.compile(locks=(StepLock(StepRef("T", 0), "B"),)), "CONFLICT")
        self.assertEqual(self.compile(), expected)


if __name__ == "__main__":
    unittest.main()
