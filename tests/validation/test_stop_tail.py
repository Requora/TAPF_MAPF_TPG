"""中文: 本测试记录停车结构检查的接受和拒绝边界, 避免将结构有效误认为安全.
English: These tests record stop-structure acceptance and rejection boundaries without implying safety.
"""
from dataclasses import replace
import unittest

from warehouse_api.contracts import Knot, MotionPlan, Pose2, RobotSegment, Twist2
from warehouse_api.validation import check_stop_tail_structure
from task_compiler.test_task_compiler import fixture


# 中文: StopTailTests 检查车队停车衔接, 以防候选漏车或在边界跳变.
# English: StopTailTests checks fleet stopping joins to prevent missing robots and boundary jumps.
class StopTailTests(unittest.TestCase):
    # 中文: setUp 创建双车停止候选, 让每个用例只改变一个约束.
    # English: setUp creates a two-robot stopping candidate so each case changes one constraint.
    def setUp(self):
        self.model, request = fixture()
        self.start = request.start
        self.prefix = tuple(RobotSegment(robot.robot_id, (
            Knot(self.start.join_state.time_s, robot.pose, robot.velocity),
            Knot(self.start.join_state.time_s + 1, robot.pose, Twist2(0, 0, 0)),
        ), ()) for robot in self.start.join_state.robots)
        self.tails = tuple(RobotSegment(segment.robot_id, (segment.knots[-1],), ())
                           for segment in self.prefix)
        self.motion = MotionPlan(self.prefix, self.tails)

    # 中文: test_accepts_stationary_tails 验证静止单节点尾段, 避免强制生成虚假停车运动.
    # English: test_accepts_stationary_tails accepts one-knot stopped tails to avoid artificial motion.
    def test_accepts_stationary_tails(self):
        self.assertEqual(check_stop_tail_structure(self.model, self.start, self.motion), ())

    # 中文: test_rejects_fleet_mismatches 检查漏车, 重复和未知 ID, 防止不完整候选通过.
    # English: test_rejects_fleet_mismatches checks missing, duplicate and unknown IDs to reject incomplete candidates.
    def test_rejects_fleet_mismatches(self):
        for tails in (self.tails[:1], self.tails + self.tails[:1],
                      (replace(self.tails[0], robot_id='unknown'), *self.tails[1:])):
            with self.subTest(tails=tails):
                self.assertTrue(check_stop_tail_structure(self.model, self.start,
                                                          replace(self.motion, stop_tail=tails)))

    # 中文: test_rejects_bad_curves 检查非法节点, 边界跳变和非零终速, 防止终点被错误视作永久静止.
    # English: test_rejects_bad_curves checks malformed knots, join jumps and nonzero terminal speed to prevent invalid permanent holds.
    def test_rejects_bad_curves(self):
        first = self.tails[0].knots[0]
        for knots in ((), (replace(first, time_s=float('nan')),), (first, first),
                      (replace(first, time_s=first.time_s + 1),),
                      (replace(first, pose=Pose2(99, 0, 0)),),
                      (first, replace(first, time_s=first.time_s + 1,
                                      velocity=Twist2(0, 0, 0.001)))):
            with self.subTest(knots=knots):
                tails = (replace(self.tails[0], knots=knots), *self.tails[1:])
                errors = check_stop_tail_structure(self.model, self.start,
                                                   replace(self.motion, stop_tail=tails))
                self.assertTrue(errors)
                self.assertEqual(errors[0].code, 'BAD_INPUT')
                self.assertIn(self.tails[0].robot_id, errors[0].related_ids)

    # 中文: test_rejects_prefix_join_and_horizon_errors 检查起点和共同边界, 防止尾段接在错误候选上.
    # English: test_rejects_prefix_join_and_horizon_errors checks initial joins and common horizons to prevent tails joining the wrong candidate.
    def test_rejects_prefix_join_and_horizon_errors(self):
        segment = self.prefix[0]
        for knots in ((replace(segment.knots[0], pose=Pose2(99, 0, 0)), segment.knots[-1]),
                      (segment.knots[0], replace(segment.knots[-1], time_s=99))):
            prefix = (replace(segment, knots=knots), *self.prefix[1:])
            self.assertTrue(check_stop_tail_structure(self.model, self.start,
                                                      replace(self.motion, common_prefix=prefix)))

    # 中文: test_check_does_not_claim_collision_safety 验证结构检查不会冒充几何检查, 保留后续安全门禁职责.
    # English: test_check_does_not_claim_collision_safety ensures structural checks do not impersonate the later geometry safety gate.
    def test_check_does_not_claim_collision_safety(self):
        tails = tuple(replace(segment, knots=(segment.knots[0], Knot(
            segment.knots[0].time_s + 2, Pose2(0, 0, 0), Twist2(0, 0, 0)),
        )) for segment in self.tails)
        self.assertEqual(check_stop_tail_structure(self.model, self.start,
                                                   replace(self.motion, stop_tail=tails)), ())

    # 中文: test_accepts_braking_and_different_stop_times 验证各车可在不同时间停车, 同时保持输入快照不变.
    # English: test_accepts_braking_and_different_stop_times allows different stopping times while preserving input snapshots.
    def test_accepts_braking_and_different_stop_times(self):
        prefix = tuple(replace(segment, knots=(segment.knots[0], replace(
            segment.knots[-1], velocity=Twist2(1, 0, 0)))) for segment in self.prefix)
        tails = tuple(RobotSegment(segment.robot_id, (segment.knots[-1], Knot(
            segment.knots[-1].time_s + index + 1,
            Pose2(index + 10, 0, 0), Twist2(0, 0, 0))), ())
            for index, segment in enumerate(prefix))
        motion = MotionPlan(prefix, tuple(reversed(tails)))
        before = repr((self.model, self.start, motion))
        self.assertEqual(check_stop_tail_structure(self.model, self.start, motion), ())
        self.assertEqual(repr((self.model, self.start, motion)), before)
