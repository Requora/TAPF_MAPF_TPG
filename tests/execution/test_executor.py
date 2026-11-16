"""中文: 本测试检查控制帧的精确切片和动作边界, 防止执行器改变计划.
English: These tests check exact control slices and action boundaries so execution preserves plans.
"""
from dataclasses import replace
import unittest
from unittest.mock import patch

from warehouse_api.contracts import (
    ExecutionInput, Failure, Knot, PhysicalAction, PhysicalState, Pose2, RobotSegment,
    RobotState, RunningAction, StepRef, TimedAction, Twist2,
)
from warehouse_api.execution import TrajectoryExecutor
from warehouse_api.trajectory import PreparedTrajectory, evaluate


# 中文: ExecutorTests 验证执行边界行为, 让错误计划显式失败而不是隐式修改.
# English: ExecutorTests checks execution-boundary behavior so invalid plans fail rather than change silently.
class ExecutorTests(unittest.TestCase):
    # 中文: setUp 建立有内部切换点的曲线和动作表, 为切片与启动测试提供独立输入.
    # English: setUp supplies a switching curve and action table as independent slice and start inputs.
    def setUp(self):
        self.zero = Twist2(0, 0, 0)
        self.knots = (Knot(0, Pose2(0, 0, 0), self.zero),
                      Knot(.3, Pose2(.2, 0, 0), Twist2(1, 0, 0)),
                      Knot(1, Pose2(1, 0, 0), self.zero))
        self.step = StepRef('T', 0)
        self.action = PhysicalAction(self.step, 'lift', 'shelf', 'node', 0, .5, ())
        self.segment = RobotSegment('A', self.knots, ())
        self.state = PhysicalState(0, (RobotState('A', self.knots[0].pose, self.zero),), (), ())
        self.data = ExecutionInput(self.state, (self.segment,), (self.action,))
        self.executor = TrajectoryExecutor()

    # 中文: test_preserves_switch_and_curve 比较切片内部状态, 防止只连端点改变运动.
    # English: test_preserves_switch_and_curve compares interior states to prevent endpoint-only refitting.
    def test_preserves_switch_and_curve(self):
        before = repr(self.data)
        frame = self.executor.build_frame(self.data, .5)
        self.assertEqual([k.time_s for k in frame.motion[0].knots], [0, .3, .5])
        original = PreparedTrajectory(self.knots)
        sliced = PreparedTrajectory(frame.motion[0].knots)
        for t in (.1, .3, .4):
            self.assertAlmostEqual(evaluate(original, t).pose.x_m, evaluate(sliced, t).pose.x_m)
            self.assertAlmostEqual(evaluate(original, t).velocity.vx_mps, evaluate(sliced, t).velocity.vx_mps)
        self.assertEqual(repr(self.data), before)

    # 中文: test_hold_after_stop 验证终点后的静止帧, 防止停车后丢失机器人.
    # English: test_hold_after_stop checks explicit holds so stopped robots remain in every frame.
    def test_hold_after_stop(self):
        state = replace(self.state, time_s=2, robots=(RobotState('A', self.knots[-1].pose, self.zero),))
        frame = self.executor.build_frame(replace(self.data, state=state), .5)
        self.assertEqual([k.time_s for k in frame.motion[0].knots], [2, 2.5])
        self.assertTrue(all(k.pose == self.knots[-1].pose for k in frame.motion[0].knots))

    # 中文: test_starts_once_and_keeps_end_boundary 验证动作只在所属步起点启动, 防止提前或每步重发.
    # English: test_starts_once_and_keeps_end_boundary checks starts only at their frame boundary to prevent early or repeated starts.
    def test_starts_once_and_keeps_end_boundary(self):
        hold = RobotSegment('A', (self.knots[0],), (TimedAction(.5, self.step),))
        data = replace(self.data, active_segments=(hold,))
        self.assertEqual(self.executor.build_frame(data, .5).start_actions, ())
        state = replace(self.state, time_s=.5)
        frame = self.executor.build_frame(replace(data, state=state), .5)
        self.assertEqual(frame.start_actions[0].action, self.action)
        running = RunningAction('A', self.step, .5, 1)
        self.assertEqual(self.executor.build_frame(replace(data, state=replace(
            state, running_actions=(running,))), .5).start_actions, ())
        self.assertEqual(self.executor.build_frame(replace(data, state=replace(state, time_s=1)), .5).start_actions, ())

    # 中文: test_rejects_invalid_inputs 检查覆盖, 时间和曲线错误, 防止缺省或外推掩盖坏输入.
    # English: test_rejects_invalid_inputs checks coverage, times and curves so defaults or extrapolation cannot hide invalid inputs.
    def test_rejects_invalid_inputs(self):
        for segments in ((), (self.segment, self.segment), (replace(self.segment, robot_id='B'),),
                         (replace(self.segment, knots=()),),
                         (replace(self.segment, knots=(self.knots[0], self.knots[0])),),
                         (replace(self.segment, knots=(replace(self.knots[0], time_s=float('nan')),)),),
                         (replace(self.segment, knots=(replace(self.knots[0], pose=Pose2(99, 0, 0)),)),),
                         (replace(self.segment, knots=(self.knots[0], self.knots[1])),)):
            with self.subTest(segments=segments):
                self.assertEqual(self.executor.build_frame(replace(self.data, active_segments=segments), .5).code, 'BAD_FRAME')
        for dt in (0, -1, float('nan'), float('inf')):
            self.assertEqual(self.executor.build_frame(self.data, dt).code, 'BAD_FRAME')

    # 中文: test_rejects_unknown_and_midframe_actions 保留动作引用和离散时钟约束, 防止静默漏发动作.
    # English: test_rejects_unknown_and_midframe_actions enforces references and clock boundaries to prevent silently dropped starts.
    def test_rejects_unknown_and_midframe_actions(self):
        for action in (TimedAction(0, StepRef('missing', 0)), TimedAction(.25, self.step)):
            data = replace(self.data, active_segments=(replace(self.segment, actions=(action,)),))
            self.assertIsInstance(self.executor.build_frame(data, .5), Failure)

    # 中文: test_prepares_once_per_active_curve 验证连续帧复用原生快照, 防止高频重建相同轨迹.
    # English: test_prepares_once_per_active_curve checks snapshot reuse across frames to avoid repeated high-frequency preparation.
    def test_prepares_once_per_active_curve(self):
        with patch('warehouse_api.execution._executor.PreparedTrajectory', wraps=PreparedTrajectory) as prepare:
            self.executor.build_frame(self.data, .5)
            knot = evaluate(PreparedTrajectory(self.knots), .5)
            state = replace(self.state, time_s=.5, robots=(RobotState('A', knot.pose, knot.velocity),))
            self.executor.build_frame(replace(self.data, state=state), .5)
            self.assertEqual(prepare.call_count, 1)

    # 中文: test_action_boundary_roundoff 检查浮点步进的边界误差, 防止真实动作因 0.1 + 0.2 不等于 0.3 而漏发.
    # English: test_action_boundary_roundoff checks floating-point tick error so 0.1 + 0.2 versus 0.3 cannot drop real starts.
    def test_action_boundary_roundoff(self):
        hold = RobotSegment('A', (self.knots[0],), (TimedAction(.3, self.step),))
        data = replace(self.data, active_segments=(hold,), state=replace(self.state, time_s=.1 + .2))
        self.assertEqual(len(self.executor.build_frame(data, .1).start_actions), 1)

    # 中文: test_rejects_busy_robot 验证新动作不能覆盖另一个运行中动作, 保留既有执行保护.
    # English: test_rejects_busy_robot prevents a new start from replacing another running action.
    def test_rejects_busy_robot(self):
        running = RunningAction('A', StepRef('old', 0), -.1, .5)
        data = replace(self.data, state=replace(self.state, running_actions=(running,)),
                       active_segments=(replace(self.segment, actions=(TimedAction(0, self.step),)),))
        self.assertEqual(self.executor.build_frame(data, .1).code, 'BAD_ACTION')

    # 中文: test_slices_full_fleet_and_replaces_branch 验证运动与保持同帧覆盖, 以及选定分支改变后不会使用旧快照.
    # English: test_slices_full_fleet_and_replaces_branch checks moving/holding fleet coverage and prevents stale snapshots after branch replacement.
    def test_slices_full_fleet_and_replaces_branch(self):
        idle = RobotSegment('B', (Knot(0, Pose2(5, 0, 0), self.zero),), ())
        state = replace(self.state, robots=(*self.state.robots, RobotState('B', idle.knots[0].pose, self.zero)))
        data = replace(self.data, state=state, active_segments=(idle, self.segment))
        frame = self.executor.build_frame(data, .5)
        self.assertEqual({motion.robot_id for motion in frame.motion}, {'A', 'B'})
        self.assertEqual(frame.motion[0].knots[-1].pose, idle.knots[0].pose)
        hold = replace(self.segment, knots=(self.knots[0],))
        frame = self.executor.build_frame(replace(self.data, active_segments=(hold,)), .5)
        self.assertEqual(frame.motion[0].knots[-1].pose, self.knots[0].pose)
