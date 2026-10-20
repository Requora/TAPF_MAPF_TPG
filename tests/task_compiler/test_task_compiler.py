"""Current-task compilation and explicit rejection traces; no solver execution."""
import copy
from dataclasses import replace
import unittest

from warehouse_api.serialization import dumps, loads
from warehouse_api.task_compiler import CurrentTaskCompiler
from warehouse_api.contracts import (
    ActionTimes, AssignmentRequest, Drop, Failure, Lift, MotionLimits, Node,
    ObjectSpec, ObjectState, PhysicalAction, PhysicalState, Pick, Place,
    PlanningStart, Point2, Polygon, Pose2, QueueState, Resource, RobotJobs,
    RobotQueue, RobotSpec, RobotState, RunningAction, Serve, SharedCompiler,
    StepLock, StepRef, Task, TaskDelta, TaskProgress, Twist2, WorldModel,
)


# 中文: 构造两机器人一货架及带锁旧任务的最小模型, 供编译测试复用, 将任务语义与路径算法隔离.
# English: Build a minimal two-robot, one-shelf model with a protected task so compiler tests
# isolate task semantics from routing algorithms.
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


# 中文: 覆盖当前任务编译, 进度和携带冲突, 为公共动作解释建立回归边界, 不提供求解器或安全验证证据.
# English: Test current-task compilation, progress and carrying conflicts as a semantic regression
# boundary, not solver or safety evidence.
class CompilerTests(unittest.TestCase):
    # 中文: 初始化独立模型, 请求和空草稿, 让每个用例从同一已接受任务出发, 避免跨用例状态影响.
    # English: Initialize an independent model, request and empty draft so every case starts from
    # the same accepted task without shared test state.
    def setUp(self):
        self.model, self.request = fixture()
        self.compiler: SharedCompiler = CurrentTaskCompiler(self.model, sim_dt_s=0.1)
        self.draft = TaskDelta((), ())

    # 中文: 只替换测试关注的请求字段再编译, 减少案例中的无关构造, 让触发条件更容易检查.
    # English: Compile a request with selected field replacements so each case highlights its
    # trigger rather than repeating unrelated setup.
    def compile(self, **changes):
        return self.compiler.compile_jobs(replace(self.request, **changes), self.draft)

    # 中文: 在保留其他规划字段时替换续接物理状态, 帮助隔离携带或在途动作条件, 避免误改请求身份.
    # English: Replace only splice-state fields so carrying and running-action cases do not
    # accidentally change planning identity.
    def state(self, **changes):
        return replace(self.request.start, join_state=replace(self.request.start.join_state, **changes))

    # 中文: 生成指定下一动作下标的进度副本, 用于剩余动作测试, 保持原已接受任务不被原地修改.
    # English: Create a progress copy at a chosen next step so remaining-action tests never mutate
    # the accepted task in place.
    def progress(self, index, **changes):
        return (replace(self.request.tasks[0], next_step=index, **changes),)

    # 中文: 统一检查失败类型, 错误码和非空原因, 保证拒绝路径可诊断, 不只检验返回值是否为空.
    # English: Check failure type, code and a nonempty reason so rejection tests require diagnostics
    # rather than merely an empty result.
    def assert_failure(self, result, code):
        self.assertIsInstance(result, Failure)
        self.assertEqual(result.code, code)
        self.assertTrue(result.message)

    # 中文: 逐字段核对完整动作和空闲机器人空作业, 保证目标, 朝向, 耗时和资源都由编译器明确输出.
    # English: Check every compiled field and idle robot's empty jobs so target, heading, duration
    # and resources are explicitly defined.
    def test_full_actions_and_idle_robot(self):
        expected = tuple(PhysicalAction(StepRef("T", i), kind, "shelf", node, yaw, 0.3, (resource,))
                         for i, (kind, node, yaw, resource) in enumerate((
                             ("lift", "home-node", 0, "home"),
                             ("serve", "station-node", 1.5, "station"),
                             ("drop", "return-node", 0, "return"))))
        self.assertEqual(self.compile(), (RobotJobs("A", expected), RobotJobs("B", ())))

    # 中文: 从已投影进度编译剩余动作, 防止编译器再次推进下标, 避免跳过服务或重复取架.
    # English: Compile from projected progress without advancing it again so service is not skipped
    # and lifting is not repeated.
    def test_projected_progress_is_not_advanced_again(self):
        carried = self.state(objects=(ObjectState("shelf", None, "A"),))
        for index in (1, 2):
            with self.subTest(next_step=index):
                result = self.compile(start=carried, tasks=self.progress(index))
                self.assertEqual([a.step.step_index for a in result[0].actions], list(range(index, 3)))
                self.assertTrue(all(a.object_id == "shelf" for a in result[0].actions))
        self.assertEqual(self.compile(tasks=self.progress(3)), (RobotJobs("A", ()), RobotJobs("B", ())))

    # 中文: 区分空候选与空旧队列, 保证前者保留绑定而后者不自动分配, 避免编译器越权做分配决策.
    # English: Distinguish an empty delta from empty existing queues so compilation preserves
    # bindings without assigning an unbound task itself.
    def test_empty_delta_keeps_binding_and_empty_queues_leave_unstarted_task_unbound(self):
        self.assertEqual(len(self.compile()[0].actions), 3)
        self.assertEqual(self.compile(queues=()), (RobotJobs("A", ()), RobotJobs("B", ())))

    # 中文: 检查动作锁独立于队列前缀仍保护执行者, 防止仅看队列锁长度就允许已承诺动作换人.
    # English: Check action locks independently of queue prefix length so a committed executor
    # cannot change merely because the queue prefix is empty.
    def test_action_lock_preserves_executor_even_with_zero_locked_prefix(self):
        lock = (StepLock(StepRef("T", 0), "A"),)
        self.assertIsInstance(self.compile(locks=lock, queues=(QueueState("A", ("T",), 0),)), tuple)
        for queues in ((), (QueueState("B", ("T",), 0),)):
            self.assert_failure(self.compile(locks=lock, queues=queues), "CONFLICT")
        for ref in (StepRef("missing", 0), StepRef("T", -1), StepRef("T", 3)):
            self.assert_failure(self.compile(locks=(StepLock(ref, "A"),)), "BAD_INPUT")

    # 中文: 覆盖携带者不匹配和载货无剩余任务, 保证物理归属与业务进度一致, 避免孤立货架无人负责.
    # English: Cover carrier mismatch and carrying without remaining work so physical ownership and
    # business progress cannot leave an orphaned shelf.
    def test_carry_ownership_and_orphaned_carry(self):
        for carrier in (None, "B"):
            obj = ObjectState("shelf", Pose2(0, 0, 0) if carrier is None else None, carrier)
            self.assert_failure(self.compile(start=self.state(objects=(obj,)), tasks=self.progress(1)), "CONFLICT")
        carried = self.state(objects=(ObjectState("shelf", None, "A"),))
        for changes in ({}, {"queues": ()}, {"tasks": self.progress(3)}):
            self.assert_failure(self.compile(start=carried, **changes), "CONFLICT")
        self.assert_failure(self.compile(tasks=self.progress(1), queues=()), "CONFLICT")

    # 中文: 确认失败后 blocked任务返回无解, 不自动重试, 将恢复决策保留给显式管理流程.
    # English: Check blocked tasks return no plan instead of retrying automatically so recovery
    # remains an explicit management decision.
    def test_blocked_current_task_does_not_retry(self):
        self.assert_failure(self.compile(tasks=self.progress(0, blocked=True)), "NO_PLAN")

    # 中文: 测试机器人已载货或货架被其他人携带时的拒绝, 同时保护诊断和快照, 防止取架校验产生副作用.
    # English: Reject loaded robots or already-carried shelves while preserving diagnostics and
    # inputs so lift precondition checks have no side effects.
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

    # 中文: 拒绝复制旧任务和修改既有队列, 保护当前实现的受限语义, 不把未实现编辑当作无害输入.
    # English: Reject old task copies and queue edits so unsupported changes are not treated as
    # harmless inputs to the current compiler.
    def test_existing_task_copies_and_queue_edits_are_rejected(self):
        draft = TaskDelta((self.request.tasks[0].task,), ())
        self.assert_failure(self.compiler.compile_jobs(self.request, draft), "CONFLICT")
        draft = TaskDelta((), (RobotQueue("A", ()),))
        self.assert_failure(self.compiler.compile_jobs(self.request, draft), "UNSUPPORTED")
        self.assert_failure(self.compile(queues=(QueueState("A", ("T", "T"), 0),)), "UNSUPPORTED")

    # 中文: 拒绝续接点仍有运行中动作, 明确剩余动作时长尚未支持, 防止把完整耗时重复附加.
    # English: Reject unfinished actions at the splice because remaining-duration handling is
    # unsupported, preventing a full action duration from being added again.
    def test_running_action_at_splice_is_rejected(self):
        start = self.state(running_actions=(RunningAction("A", StepRef("T", 0), 9, 11),))
        self.assert_failure(self.compile(start=start), "UNSUPPORTED")

    # 中文: 覆盖非法下标, 绑定和重复 ID, 保证进入业务编译前引用一致, 防止字典覆盖隐藏坏快照.
    # English: Check invalid progress, bindings and duplicate IDs so inconsistent references cannot
    # be hidden by dictionary overwrites.
    def test_progress_binding_and_duplicate_id_errors(self):
        for index in (-1, 4):
            self.assert_failure(self.compile(tasks=self.progress(index)), "BAD_INPUT")
        for queues in ((QueueState("A", ("T",), 2),), (QueueState("unknown", (), 0),),
                       (QueueState("A", ("missing",), 0),), self.request.queues * 2,
                       (QueueState("A", ("T",), 0), QueueState("B", ("T",), 0))):
            self.assert_failure(self.compile(queues=queues), "BAD_INPUT")
        self.assert_failure(self.compile(tasks=self.request.tasks * 2), "BAD_INPUT")

    # 中文: 拒绝缺失实体和矛盾货架位置, 确保编译从完整物理快照开始, 避免对未知携带状态作猜测.
    # English: Reject missing entities and contradictory shelf locations so compilation starts from
    # complete physical state without guessing ownership.
    def test_incomplete_and_inconsistent_physical_state(self):
        state = self.request.start.join_state
        for changes in ({"robots": state.robots[:1]}, {"robots": state.robots * 2},
                        {"objects": ()}, {"objects": state.objects * 2},
                        {"objects": (ObjectState("shelf", None, None),)},
                        {"objects": (ObjectState("shelf", Pose2(0, 0, 0), "A"),)},
                        {"objects": (ObjectState("shelf", None, "unknown"),)}):
            self.assert_failure(self.compile(start=self.state(**changes)), "BAD_INPUT")

    # 中文: 给两台机器人绑定同一货架任务, 验证冲突检测跨任务生效, 防止分别合法的任务组合成非法候选.
    # English: Bind two tasks to one shelf to check cross-task conflicts so individually valid tasks
    # cannot form an invalid combined candidate.
    def test_duplicate_shelf_claims(self):
        task = replace(self.request.tasks[0].task, id="T2")
        self.assert_failure(self.compile(tasks=self.request.tasks + (TaskProgress(task, 0, False),),
                                        queues=self.request.queues + (QueueState("B", ("T2",), 0),)), "CONFLICT")

    # 中文: 覆盖非标准任务, 偏置携带和模糊取架位姿, 确认显式 UNSUPPORTED, 防止近似解释未支持能力.
    # English: Cover unsupported task shapes, carry offsets and pickup poses so capability gaps are
    # rejected rather than approximated silently.
    def test_unsupported_task_shape_offset_and_pickup_pose(self):
        task = replace(self.request.tasks[0].task, steps=(Drop("return"),))
        self.assert_failure(self.compile(tasks=self.progress(0, task=task)), "UNSUPPORTED")
        self.assert_failure(self.compile(start=self.state(objects=(ObjectState("shelf", Pose2(0.01, 0, 0), None),))), "UNSUPPORTED")
        for model in (replace(self.model, objects=(replace(self.model.objects[0], carry_offset=Pose2(1, 0, 0)),)),
                      replace(self.model, places=self.model.places + (replace(self.model.places[0], id="alias"),))):
            compiler = CurrentTaskCompiler(model, sim_dt_s=0.1)
            self.assert_failure(compiler.compile_jobs(self.request, self.draft), "UNSUPPORTED")

    # 中文: 注入未知货架或错误位置用途, 确认输入错误在目标解析前后均可见, 防止动作去错服务点.
    # English: Inject unknown shelves and wrong place kinds so target errors remain visible instead
    # of sending an action to the wrong service location.
    def test_unknown_shelf_and_wrong_place_kind(self):
        for index, action in ((0, Lift("missing")), (1, Serve("home", (Pick("O", "X", 1),))),
                              (2, Drop("station")), (2, Drop("missing"))):
            steps = list(self.request.tasks[0].task.steps)
            steps[index] = action
            task = replace(self.request.tasks[0].task, steps=tuple(steps))
            self.assert_failure(self.compile(tasks=self.progress(0, task=task)), "BAD_INPUT")

    # 中文: 检查模型结构和配置错误直接抛出原异常, 维护开发调试边界, 不将程序错误泛化成求解失败.
    # English: Check that model-shape and configuration errors preserve original exceptions so
    # programming faults are not disguised as planning failures.
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

    # 中文: 在重复调用, JSON重放和失败后比较结果与输入, 保证编译是纯候选转换, 不暗中推进实时状态.
    # English: Compare results and inputs across repeated calls, JSON replay and failure so
    # compilation stays a pure candidate transformation.
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
