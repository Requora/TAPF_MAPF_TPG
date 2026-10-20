"""Candidate compilation traces, including rejection without partial results."""
import copy
from dataclasses import replace
import unittest

from .test_compiler import fixture
from warehouse_api.codec import dumps, loads
from warehouse_api.compiler import CurrentTaskCompiler
from warehouse_api.contracts import (
    AssignmentRequest, Drop, Failure, Lift, ObjectState, Pose2, QueueState,
    RobotQueue, StepLock, StepRef, TaskDelta, TaskProgress,
)


class CandidateBindingTests(unittest.TestCase):
    def setUp(self):
        self.model, accepted = fixture()
        self.task = replace(accepted.tasks[0].task, id="new-task")
        self.request = replace(accepted, tasks=(), queues=())
        self.draft = TaskDelta((self.task,), (RobotQueue("B", (self.task.id,)),))
        self.compiler = CurrentTaskCompiler(self.model, sim_dt_s=0.1)

    def compile(self, request=None, draft=None):
        request = self.request if request is None else request
        draft = self.draft if draft is None else draft
        before = copy.deepcopy((self.model, request, draft))
        result = self.compiler.compile_jobs(request, draft)
        self.assertEqual((self.model, request, draft), before)
        return result

    def assert_failure(self, result, code, message, ids):
        self.assertEqual(result, Failure(code, message, ids))

    def test_new_task_matches_accepted_task_compilation(self):
        accepted = replace(self.request, tasks=(TaskProgress(self.task, 0, False),),
                           queues=(QueueState("B", (self.task.id,), 0),))
        expected = self.compiler.compile_jobs(accepted, TaskDelta((), ()))
        for queues in ((), (QueueState("B", (), 0),)):
            result = self.compile(replace(self.request, queues=queues))
            self.assertEqual(result, expected)
            self.assertEqual(result[0].actions, ())
            self.assertEqual([action.step for action in result[1].actions],
                             [StepRef("new-task", i) for i in range(3)])

    def test_existing_locked_carried_task_is_preserved(self):
        model, accepted = fixture()
        extra = replace(model.objects[0], id="second-shelf")
        self.model = replace(model, objects=model.objects + (extra,))
        self.compiler = CurrentTaskCompiler(self.model, sim_dt_s=0.1)
        state = replace(accepted.start.join_state, objects=(
            ObjectState("shelf", None, "A"), ObjectState("second-shelf", Pose2(0, 0, 0), None),
        ))
        request = replace(accepted, start=replace(accepted.start, join_state=state),
                          tasks=(replace(accepted.tasks[0], next_step=1),),
                          locks=(StepLock(StepRef("T", 0), "A"),))
        task = replace(self.task, steps=(Lift("second-shelf"), *self.task.steps[1:]))
        draft = replace(self.draft, tasks=(task,))
        old_jobs = self.compiler.compile_jobs(request, TaskDelta((), ()))
        result = self.compile(request, draft)
        self.assertEqual(result[0], old_jobs[0])
        self.assertEqual([a.step.step_index for a in result[0].actions], [1, 2])
        self.assertEqual([a.object_id for a in result[1].actions], ["second-shelf"] * 3)

    def test_duplicate_new_ids_and_existing_id_reuse(self):
        self.assert_failure(self.compile(draft=replace(self.draft, tasks=(self.task,) * 2)),
                            "BAD_INPUT", "Duplicate candidate task ID", (self.task.id,) * 2)
        for next_step in (0, 3):
            request = replace(self.request, tasks=(TaskProgress(self.task, next_step, False),))
            self.assert_failure(self.compile(request), "CONFLICT",
                                "Candidate task ID already exists", (self.task.id,))

    def test_duplicate_and_unknown_candidate_robot(self):
        self.assert_failure(self.compile(draft=replace(self.draft, queues=self.draft.queues * 2)),
                            "BAD_INPUT", "Duplicate candidate queue robot", ("B", "B"))
        draft = replace(self.draft, queues=(RobotQueue("missing", (self.task.id,)),))
        self.assert_failure(self.compile(draft=draft), "BAD_INPUT", "Unknown candidate robot", ("missing",))

    def test_new_tasks_require_exactly_one_executor(self):
        self.assert_failure(self.compile(draft=replace(self.draft, queues=())),
                            "BAD_INPUT", "Candidate task has no executor", (self.task.id,))
        queues = (RobotQueue("A", (self.task.id,)), RobotQueue("B", (self.task.id,)))
        self.assert_failure(self.compile(draft=replace(self.draft, queues=queues)),
                            "BAD_INPUT", "Candidate task has multiple executors", (self.task.id,))
        draft = replace(self.draft, tasks=())
        self.assert_failure(self.compile(draft=draft), "BAD_INPUT", "Unknown candidate task", (self.task.id,))

    def test_empty_suffix_and_multiple_tasks_remain_unsupported(self):
        for ids in ((), (self.task.id, self.task.id)):
            draft = replace(self.draft, queues=(RobotQueue("B", ids),))
            self.assert_failure(self.compile(draft=draft), "UNSUPPORTED",
                                "Candidate binding requires exactly one task", ("B",))

    def test_occupied_robot_cannot_be_replaced_or_extended(self):
        _, request = fixture()
        for locked in (0, 1):
            for next_step in (0, 3):
                current = replace(request, queues=(QueueState("A", ("T",), locked),),
                                  tasks=(replace(request.tasks[0], next_step=next_step),))
                draft = replace(self.draft, queues=(RobotQueue("A", (self.task.id,)),))
                self.assert_failure(self.compile(current, draft), "UNSUPPORTED",
                                    "Existing current bindings cannot be edited", ("A",))

    def test_existing_unbound_tasks_cannot_be_assigned(self):
        request = replace(self.request, tasks=(TaskProgress(self.task, 0, False),))
        self.assert_failure(self.compile(request, replace(self.draft, tasks=())), "UNSUPPORTED",
                            "Only newly defined tasks can be assigned", (self.task.id,))

    def test_invalid_old_action_lock_is_not_repaired_by_draft(self):
        _, request = fixture()
        request = replace(request, locks=(StepLock(StepRef("T", 0), "B"),))
        self.assert_failure(self.compile(request), "CONFLICT",
                            "Committed action executor must be preserved", ("T", "B"))

    def test_candidate_cannot_claim_accepted_or_other_candidate_shelf(self):
        _, request = fixture()
        self.assert_failure(self.compile(request), "CONFLICT",
                            "Concurrent tasks claim the same shelf", (self.task.id, "shelf"))
        second = replace(self.task, id="second-task")
        draft = TaskDelta((self.task, second), (
            RobotQueue("A", (self.task.id,)), RobotQueue("B", (second.id,)),
        ))
        self.assert_failure(self.compile(draft=draft), "CONFLICT",
                            "Concurrent tasks claim the same shelf", (second.id, "shelf"))

    def test_candidate_uses_existing_action_and_target_validation(self):
        for task, code, message, ids in (
            (replace(self.task, steps=()), "UNSUPPORTED",
             "Empty candidate tasks are not supported", (self.task.id,)),
            (replace(self.task, steps=(Drop("return"),)), "UNSUPPORTED",
             "Expected one Lift, Serve, Drop sequence", (self.task.id,)),
            (replace(self.task, steps=(*self.task.steps[:2], Drop("missing"))), "BAD_INPUT",
             "Expected a known storage place", ("missing",)),
        ):
            self.assert_failure(self.compile(draft=replace(self.draft, tasks=(task,))), code, message, ids)
        state = replace(self.request.start.join_state, objects=(ObjectState("shelf", None, "B"),))
        request = replace(self.request, start=replace(self.request.start, join_state=state))
        self.assert_failure(self.compile(request), "CONFLICT",
                            "Lift requires an empty robot and grounded shelf", ("B", "shelf"))

    def test_replay_and_failure_do_not_change_future_results(self):
        expected = self.compile()
        request = loads(AssignmentRequest, dumps(self.request))
        draft = loads(TaskDelta, dumps(self.draft))
        self.assertEqual(self.compile(request, draft), expected)
        self.assertIsInstance(self.compile(draft=replace(draft, queues=())), Failure)
        self.assertEqual(self.compile(), expected)


if __name__ == "__main__":
    unittest.main()
