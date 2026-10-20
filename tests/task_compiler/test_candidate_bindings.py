"""Candidate compilation traces, including rejection without partial results."""
import copy
from dataclasses import replace
import unittest

from .test_task_compiler import fixture
from warehouse_api.serialization import dumps, loads
from warehouse_api.task_compiler import CurrentTaskCompiler
from warehouse_api.contracts import (
    AssignmentRequest, Drop, Failure, Lift, ObjectState, Pose2, QueueState,
    RobotQueue, StepLock, StepRef, TaskDelta, TaskProgress,
)


# 中文: CandidateBindingTests 测试类验证空闲机器人新任务绑定及旧承诺保护, 为编译器的增量入口提供反例, 防止新任务覆盖已接受状态.
# English: CandidateBindingTests tests new-task bindings on idle robots and protection of old commitments so candidate
# additions cannot overwrite accepted state.
class CandidateBindingTests(unittest.TestCase):
    # 中文: setUp 方法准备空闲机器人和唯一新任务草稿, 作为合法候选基线, 让每个拒绝案例只改动相关条件.
    # English: setUp prepares an idle robot and one new-task draft as a valid baseline so each rejection
    # case changes only the relevant condition.
    def setUp(self):
        self.model, accepted = fixture()
        self.task = replace(accepted.tasks[0].task, id="new-task")
        self.request = replace(accepted, tasks=(), queues=())
        self.draft = TaskDelta((self.task,), (RobotQueue("B", (self.task.id,)),))
        self.compiler = CurrentTaskCompiler(self.model, sim_dt_s=0.1)

    # 中文: compile 方法调用编译器并统一检查所有输入不变, 为正反案例复用快照保护, 防止失败路径偷偷写状态.
    # English: compile compiles and checks all inputs remain unchanged so successful and failed cases share
    # protection against hidden state mutation.
    def compile(self, request=None, draft=None):
        request = self.request if request is None else request
        draft = self.draft if draft is None else draft
        before = copy.deepcopy((self.model, request, draft))
        result = self.compiler.compile_jobs(request, draft)
        self.assertEqual((self.model, request, draft), before)
        return result

    # 中文: assert_failure 方法同时核对失败码, 原因和关联 ID, 保护可诊断性, 避免只返回泛化错误也让测试通过.
    # English: assert_failure checks failure code, message and related IDs together so a generic error cannot
    # satisfy a diagnostic regression test.
    def assert_failure(self, result, code, message, ids):
        self.assertEqual(result, Failure(code, message, ids))

    # 中文: 本测试比较新任务和已接受任务的编译结果, 保证两种入口共享动作解释, 避免新绑定改变时长或引用.
    # English: This test compares new and accepted task compilation so both paths share action semantics
    # instead of changing durations or references.
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

    # 中文: 本测试在旧机器人载货且有锁时增加另一新任务, 检查旧作业完全不变, 防止增量绑定扰动已承诺责任.
    # English: This test adds a new task alongside a locked carrying task and checks old jobs remain identical
    # so incremental allocation cannot disturb commitments.
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

    # 中文: 本测试验证系统拒绝候选重复 ID 及复用旧 ID, 保持任务身份稳定, 防止进度和锁引用到另一份定义.
    # English: This test checks rejection of duplicate or reused task IDs so progress and locks cannot accidentally refer
    # to a different task definition.
    def test_duplicate_new_ids_and_existing_id_reuse(self):
        self.assert_failure(self.compile(draft=replace(self.draft, tasks=(self.task,) * 2)),
                            "BAD_INPUT", "Duplicate candidate task ID", (self.task.id,) * 2)
        for next_step in (0, 3):
            request = replace(self.request, tasks=(TaskProgress(self.task, next_step, False),))
            self.assert_failure(self.compile(request), "CONFLICT",
                                "Candidate task ID already exists", (self.task.id,))

    # 中文: 本测试验证系统拒绝重复或未知机器人队列, 保证候选执行者唯一可追溯, 防止编译时覆盖同名结果.
    # English: This test checks rejection of duplicate or unknown robot queues so candidate ownership stays unique and
    # output cannot be overwritten by duplicate bindings.
    def test_duplicate_and_unknown_candidate_robot(self):
        self.assert_failure(self.compile(draft=replace(self.draft, queues=self.draft.queues * 2)),
                            "BAD_INPUT", "Duplicate candidate queue robot", ("B", "B"))
        draft = replace(self.draft, queues=(RobotQueue("missing", (self.task.id,)),))
        self.assert_failure(self.compile(draft=draft), "BAD_INPUT", "Unknown candidate robot", ("missing",))

    # 中文: 本测试检查新任务不能漏绑, 多绑或引用缺失定义, 保证每份候选工作恰有一个执行者.
    # English: This test checks missing, multiple and undefined task bindings so each candidate task has
    # exactly one accountable executor.
    def test_new_tasks_require_exactly_one_executor(self):
        self.assert_failure(self.compile(draft=replace(self.draft, queues=())),
                            "BAD_INPUT", "Candidate task has no executor", (self.task.id,))
        queues = (RobotQueue("A", (self.task.id,)), RobotQueue("B", (self.task.id,)))
        self.assert_failure(self.compile(draft=replace(self.draft, queues=queues)),
                            "BAD_INPUT", "Candidate task has multiple executors", (self.task.id,))
        draft = replace(self.draft, tasks=())
        self.assert_failure(self.compile(draft=draft), "BAD_INPUT", "Unknown candidate task", (self.task.id,))

    # 中文: 本测试验证编译器明确拒绝不含新任务的队列后缀和多任务队列, 保持当前单任务子集的边界, 防止未实现调度被误当成功.
    # English: This test checks rejection of queue suffixes with no new tasks and multi-task queues explicitly so unimplemented scheduling is
    # not mistaken for supported behavior.
    def test_empty_suffix_and_multiple_tasks_remain_unsupported(self):
        for ids in ((), (self.task.id, self.task.id)):
            draft = replace(self.draft, queues=(RobotQueue("B", ids),))
            self.assert_failure(self.compile(draft=draft), "UNSUPPORTED",
                                "Candidate binding requires exactly one task", ("B",))

    # 中文: 本测试检查已有队列的机器人不能被新绑定覆盖或追加, 即使任务预测完成也保持限制, 避免隐式队列编辑.
    # English: This test checks that existing robot queues cannot be replaced or extended, even after projected
    # completion, so queue editing is never implicit.
    def test_occupied_robot_cannot_be_replaced_or_extended(self):
        _, request = fixture()
        for locked in (0, 1):
            for next_step in (0, 3):
                current = replace(request, queues=(QueueState("A", ("T",), locked),),
                                  tasks=(replace(request.tasks[0], next_step=next_step),))
                draft = replace(self.draft, queues=(RobotQueue("A", (self.task.id,)),))
                self.assert_failure(self.compile(current, draft), "UNSUPPORTED",
                                    "Existing current bindings cannot be edited", ("A",))

    # 中文: 本测试验证系统拒绝把旧未绑定任务当新任务分配, 明确当前入口只接受新定义, 防止绕过受保护的任务生命周期.
    # English: This test checks rejection of reassignment of old unbound tasks so the new-task-only boundary cannot bypass
    # accepted task lifecycle rules.
    def test_existing_unbound_tasks_cannot_be_assigned(self):
        request = replace(self.request, tasks=(TaskProgress(self.task, 0, False),))
        self.assert_failure(self.compile(request, replace(self.draft, tasks=())), "UNSUPPORTED",
                            "Only newly defined tasks can be assigned", (self.task.id,))

    # 中文: 本测试确认已有动作锁有误时, 编译器仍拒绝合法的新草稿. 编译器必须先验证已接受状态, 防止新候选掩盖已有执行承诺冲突.
    # English: This test checks rejection of an invalid old action lock even with a valid draft so candidate overlay cannot
    # conceal a broken commitment baseline.
    def test_invalid_old_action_lock_is_not_repaired_by_draft(self):
        _, request = fixture()
        request = replace(request, locks=(StepLock(StepRef("T", 0), "B"),))
        self.assert_failure(self.compile(request), "CONFLICT",
                            "Committed action executor must be preserved", ("T", "B"))

    # 中文: 本测试制造候选与旧任务及候选之间的货架竞争, 确保唯一占用, 防止两台机器人计划搬同一架.
    # English: This test creates accepted/candidate and candidate/candidate shelf conflicts so two robots
    # cannot be assigned the same shelf concurrently.
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

    # 中文: 本测试让新任务触发旧动作及目标校验, 证明没有较宽松的候选旁路, 防止不合法取放进入路径规划.
    # English: This test exercises existing action and target checks through new tasks so candidate compilation
    # cannot bypass handling constraints.
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

    # 中文: 本测试在 JSON 重放和一次失败后重新编译合法输入, 检查结果一致, 防止候选缓存或临时状态污染后续请求.
    # English: This test recompiles valid input after JSON replay and failure so cached or temporary candidate
    # state cannot contaminate future results.
    def test_replay_and_failure_do_not_change_future_results(self):
        expected = self.compile()
        request = loads(AssignmentRequest, dumps(self.request))
        draft = loads(TaskDelta, dumps(self.draft))
        self.assertEqual(self.compile(request, draft), expected)
        self.assertIsInstance(self.compile(draft=replace(draft, queues=())), Failure)
        self.assertEqual(self.compile(), expected)


if __name__ == "__main__":
    unittest.main()
