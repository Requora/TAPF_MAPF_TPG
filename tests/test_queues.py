"""Queue candidate checks; these do not establish executable feasibility."""
import copy
from dataclasses import replace
import unittest

from warehouse_api.codec import dumps, loads
from warehouse_api.contracts import (
    AssignmentRequest, Demand, Failure, Lift, PhysicalState, PlanningStart,
    Pose2, QueueState, RobotQueue, RobotSegment, RobotState, StepLock, StepRef,
    Stock, Task, TaskDelta, TaskProgress, TimedAction, Twist2,
)
from warehouse_api.queues import candidate_queues


def request_fixture():
    robots = tuple(RobotState(robot, Pose2(0, 0, 0), Twist2(0, 0, 0))
                   for robot in ("R1", "R2", "R3"))
    state = PhysicalState(2, robots, (), ())
    start = PlanningStart("round-1", 7, 0, state, (), 1)
    tasks = tuple(TaskProgress(Task(task, (Lift("P" + task),)), 0, False)
                  for task in ("A", "B", "C", "U"))
    return AssignmentRequest(
        start, (Demand("O1", "X", 4, None),), (Stock("PA", "X", 4),),
        tasks, (QueueState("R1", ("A", "B"), 1), QueueState("R2", ("C",), 0)),
        (), 1,
    )


class CandidateQueueTests(unittest.TestCase):
    def setUp(self):
        self.request = request_fixture()
        self.empty = TaskDelta((), ())

    def assert_failure(self, request, draft, code, message):
        before = copy.deepcopy((request, draft))
        result = candidate_queues(request, draft)
        self.assertIsInstance(result, Failure)
        self.assertEqual(result.code, code)
        self.assertIn(message, result.message)
        self.assertTrue(result.related_ids)
        self.assertEqual((request, draft), before)

    def test_omission_and_idle_robot_order(self):
        self.assertEqual(candidate_queues(self.request, self.empty), (
            RobotQueue("R1", ("A", "B")), RobotQueue("R2", ("C",)), RobotQueue("R3", ()),
        ))

    def test_suffix_replacement_and_empty_suffix_preserve_prefix(self):
        for suffix in ((), ("U",), ("U", "B")):
            with self.subTest(suffix=suffix):
                draft = TaskDelta((), (RobotQueue("R1", suffix),))
                self.assertEqual(candidate_queues(self.request, draft)[0],
                                 RobotQueue("R1", ("A",) + suffix))
        request = replace(self.request, queues=(QueueState("R1", ("A", "B"), 2),))
        result = candidate_queues(request, TaskDelta((), (RobotQueue("R1", ("U",)),)))
        self.assertEqual(result[0], RobotQueue("R1", ("A", "B", "U")))

    def test_atomic_transfer_is_independent_of_edit_order(self):
        edits = (RobotQueue("R1", ()), RobotQueue("R2", ("B", "C")))
        for queues in (edits, edits[::-1]):
            self.assertEqual(candidate_queues(self.request, TaskDelta((), queues)), (
                RobotQueue("R1", ("A",)), RobotQueue("R2", ("B", "C")), RobotQueue("R3", ()),
            ))

    def test_new_and_unbound_tasks_can_be_assigned(self):
        draft = TaskDelta((Task("N", (Lift("PN"),)),), (RobotQueue("R3", ("U", "N")),))
        self.assertEqual(candidate_queues(self.request, draft)[2], RobotQueue("R3", ("U", "N")))
        self.assertNotIsInstance(candidate_queues(self.request, replace(draft, queues=())), Failure)

    def test_definition_reuse_unknown_references_and_duplicate_edits(self):
        new = Task("N", (Lift("PN"),))
        cases = (
            (TaskDelta((self.request.tasks[0].task,), ()), "not new"),
            (TaskDelta((new, new), ()), "not new"),
            (TaskDelta((), (RobotQueue("R1", ("missing",)),)), "unknown task"),
            (TaskDelta((), (RobotQueue("missing", ()),)), "draft queue robot"),
            (TaskDelta((), (RobotQueue("R1", ()), RobotQueue("R1", ()))), "draft queue robot"),
        )
        for draft, message in cases:
            with self.subTest(draft=draft):
                self.assert_failure(self.request, draft, "BAD_INPUT", message)

    def test_duplicate_ownership_including_omitted_and_protected_queues(self):
        for queues in ((RobotQueue("R3", ("B",)),), (RobotQueue("R3", ("U", "U")),),
                       (RobotQueue("R1", ("A",)),),
                       (RobotQueue("R1", ()), RobotQueue("R3", ("A",)))):
            with self.subTest(queues=queues):
                self.assert_failure(self.request, TaskDelta((), queues), "CONFLICT", "more than once")

    def test_step_lock_protects_executor_without_freezing_other_suffix_tasks(self):
        lock = StepLock(StepRef("B", 0), "R1")
        request = replace(self.request, locks=(lock,))
        self.assertNotIsInstance(candidate_queues(request, self.empty), Failure)
        draft = TaskDelta((), (RobotQueue("R1", ("B", "U")),))
        self.assertEqual(candidate_queues(request, draft)[0], RobotQueue("R1", ("A", "B", "U")))
        for edits in ((RobotQueue("R1", ()),),
                      (RobotQueue("R1", ()), RobotQueue("R3", ("B",)))):
            self.assert_failure(request, TaskDelta((), edits), "CONFLICT", "executor")

    def test_bad_lock_references_and_inconsistent_old_owners(self):
        for lock in (StepLock(StepRef("missing", 0), "R1"),
                     StepLock(StepRef("B", -1), "R1"), StepLock(StepRef("B", 1), "R1"),
                     StepLock(StepRef("B", True), "R1"), StepLock(StepRef("B", 0.0), "R1")):
            self.assert_failure(replace(self.request, locks=(lock,)), self.empty,
                                "BAD_INPUT", "reference")
        for task, robot in (("B", "R2"), ("B", "missing"), ("U", "R1")):
            lock = StepLock(StepRef(task, 0), robot)
            self.assert_failure(replace(self.request, locks=(lock,)), self.empty,
                                "BAD_INPUT", "old task owner")
        lock = StepLock(StepRef("B", 0), "R1")
        self.assert_failure(replace(self.request, locks=(lock, lock)), self.empty,
                            "BAD_INPUT", "Duplicate StepLock")

    def test_invalid_old_snapshots_are_rejected_before_edits(self):
        for count in (-1, 3, True, 1.5):
            request = replace(self.request, queues=(QueueState("R1", ("A", "B"), count),))
            self.assert_failure(request, self.empty, "BAD_INPUT", "prefix count")
        for queues, message in (
            ((QueueState("missing", (), 0),), "old queue robot"),
            ((self.request.queues[0], self.request.queues[0]), "old queue robot"),
            ((QueueState("R1", ("missing",), 0),), "unknown task"),
            ((QueueState("R1", ("A", "A"), 0),), "more than once"),
            ((QueueState("R1", ("A",), 0), QueueState("R2", ("A",), 0)), "more than once"),
        ):
            self.assert_failure(replace(self.request, queues=queues), self.empty, "BAD_INPUT", message)
        self.assert_failure(replace(self.request, tasks=self.request.tasks * 2), self.empty,
                            "BAD_INPUT", "accepted task ID")
        state = self.request.start.join_state
        start = replace(self.request.start, join_state=replace(state, robots=state.robots * 2))
        self.assert_failure(replace(self.request, start=start), self.empty, "BAD_INPUT", "robot ID")

    def test_success_and_failure_leave_progress_motion_and_ledgers_unchanged(self):
        progress = replace(self.request.tasks[1], next_step=1, blocked=True)
        fixed = RobotSegment("R1", (), (TimedAction(0, StepRef("A", 0)),))
        request = replace(self.request, tasks=(self.request.tasks[0], progress),
                          queues=(self.request.queues[0],),
                          start=replace(self.request.start, fixed_prefix=(fixed,)))
        before = copy.deepcopy(request)
        draft = TaskDelta((), (RobotQueue("R1", ()), RobotQueue("R2", ("B",))))
        self.assertNotIsInstance(candidate_queues(request, draft), Failure)
        self.assertEqual(request, before)
        self.assert_failure(request, TaskDelta((), (RobotQueue("R3", ("A",)),)),
                            "CONFLICT", "more than once")

    def test_json_replay_and_empty_fleet(self):
        request = loads(AssignmentRequest, dumps(self.request))
        draft = loads(TaskDelta, dumps(TaskDelta((), (RobotQueue("R1", ()),))))
        result = candidate_queues(request, draft)
        self.assertEqual(loads(tuple[RobotQueue, ...], dumps(result)), result)
        state = replace(request.start.join_state, robots=())
        request = replace(request, start=replace(request.start, join_state=state), queues=())
        self.assertEqual(candidate_queues(request, self.empty), ())


if __name__ == "__main__":
    unittest.main()
