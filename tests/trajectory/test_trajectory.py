"""中文: 本模块用解析曲线检查轨迹读取和切片, 避免用规划成功代替曲线一致性.
English: This module checks evaluation and slicing against analytic curves rather than planner success.
"""
from dataclasses import replace
import math
import unittest

from warehouse_api.contracts import Knot, Pose2, Twist2
from warehouse_api.trajectory import evaluate, slice_curve


# 中文: cubic 定义独立的解析位置与导数, 为三个坐标及未折返朝向提供测试基准.
# English: cubic supplies independent analytic positions and derivatives to test all axes and unwrapped yaw.
def cubic(t):
    return Knot(t, Pose2(t**3, 2*t*t, 6 + t**3), Twist2(3*t*t, 4*t, 3*t*t))


# 中文: TrajectoryTests 验证曲线的连续语义和拒绝边界, 防止切片改变已规划运动.
# English: TrajectoryTests checks curve semantics and rejection boundaries so slices cannot change planned motion.
class TrajectoryTests(unittest.TestCase):
    # 中文: assert_knot 比较节点的全部状态分量, 让位置和速度错误都能被发现.
    # English: assert_knot compares every state component so both position and velocity errors are observable.
    def assert_knot(self, actual, expected):
        self.assertEqual(actual.time_s, expected.time_s)
        for a, b in zip((actual.pose.x_m, actual.pose.y_m, actual.pose.yaw_rad,
                         actual.velocity.vx_mps, actual.velocity.vy_mps, actual.velocity.omega_radps),
                        (expected.pose.x_m, expected.pose.y_m, expected.pose.yaw_rad,
                         expected.velocity.vx_mps, expected.velocity.vy_mps, expected.velocity.omega_radps)):
            self.assertAlmostEqual(a, b, places=11)

    # 中文: 本测试用独立三次多项式和导数检查段内状态, 防止线性插值或朝向折返.
    # English: This test checks interior states against independent cubics and derivatives, rejecting linear interpolation and yaw wrapping.
    def test_evaluation_matches_analytic_curve(self):
        curve = (cubic(0), cubic(2))
        for t in (0, 0.1, 0.5, 1, 1.9, 2):
            self.assert_knot(evaluate(curve, t), cubic(t))

    # 中文: 本测试检查嵌套切片与解析曲线一致且输入不变, 防止反复截取引入新运动.
    # English: This test checks nested slices against the analytic curve and preserves input to prevent refitting motion.
    def test_slice_preserves_curve_and_input(self):
        curve = (cubic(0), cubic(1), cubic(2))
        original = tuple(curve)
        sliced = slice_curve(curve, 0.2, 1.8)
        self.assertEqual(tuple(k.time_s for k in sliced), (0.2, 1, 1.8))
        nested = slice_curve(sliced, 0.4, 1.6)
        for i in range(21):
            t = 0.4 + 1.2*i/20
            self.assert_knot(evaluate(nested, t), cubic(t))
        self.assertEqual(curve, original)

    # 中文: 本测试保留加速到减速的切换点, 防止两端静止的运动被错误重拟合.
    # English: This test retains the acceleration-to-braking switch so a rest-to-rest motion is not refitted.
    def test_acceleration_switch_and_terminal_hold(self):
        curve = (Knot(0, Pose2(0, 0, 0), Twist2(0, 0, 0)),
                 Knot(1, Pose2(0.5, 0, 0), Twist2(1, 0, 0)),
                 Knot(2, Pose2(1, 0, 0), Twist2(0, 0, 0)))
        sliced = slice_curve(curve, 0.5, 3)
        self.assertEqual(sliced[1:3], curve[1:])
        for t, x, v in ((0.5, 0.125, 0.5), (1.5, 0.875, 0.5), (2.5, 1, 0)):
            self.assert_knot(evaluate(sliced, t), Knot(t, Pose2(x, 0, 0), Twist2(v, 0, 0)))
        self.assertEqual(slice_curve(curve, 1, 2), curve[1:])
        self.assertEqual(evaluate((curve[-1],), 10), replace(curve[-1], time_s=10))

    # 中文: 本测试只允许读取移动单节点的精确时刻, 防止零长度前缀被当作无限运动.
    # English: This test permits a moving singleton only at its instant so a zero-duration prefix cannot imply indefinite motion.
    def test_moving_endpoint_does_not_authorize_extrapolation(self):
        self.assertEqual(evaluate((cubic(1),), 1), cubic(1))
        for curve in ((cubic(1),), (cubic(0), cubic(1))):
            with self.assertRaises(ValueError):
                evaluate(curve, math.nextafter(1, math.inf))
        tiny_motion = replace(cubic(1), velocity=Twist2(1e-12, 0, 0))
        with self.assertRaises(ValueError):
            evaluate((tiny_motion,), 2)

    # 中文: 本测试拒绝坏节点和非法时间范围, 防止 NaN 或静默截断进入执行数据.
    # English: This test rejects invalid knots and time ranges so NaN and silent clamping cannot enter execution data.
    def test_invalid_inputs(self):
        for curve in ((), (cubic(1), cubic(0)), (cubic(0), cubic(0)),
                      (replace(cubic(0), pose=Pose2(math.nan, 0, 0)),),
                      (replace(cubic(0), velocity=Twist2(0, math.inf, 0)),),
                      (replace(cubic(0), time_s=math.inf),)):
            with self.subTest(curve=curve), self.assertRaises(ValueError):
                evaluate(curve, 0)
        for t in (-1e-12, math.nan, math.inf, -math.inf):
            with self.subTest(t=t), self.assertRaises(ValueError):
                evaluate((cubic(0), cubic(1)), t)
        for start, end in ((0, 0), (1, 0), (0, math.nan), (math.nan, 1), (0, math.inf)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                slice_curve((cubic(0), cubic(1)), start, end)

    # 中文: 本测试保留很短的正时长段, 防止时间容差把真实运动吸附到端点.
    # English: This test preserves short positive intervals so time tolerances cannot snap real motion to endpoints.
    def test_short_interval_is_not_snapped(self):
        curve = (Knot(0, Pose2(0, 0, 0), Twist2(1, 0, 0)),
                 Knot(1e-10, Pose2(1e-10, 0, 0), Twist2(1, 0, 0)))
        result = evaluate(curve, 5e-11)
        self.assertEqual(result.pose.x_m, 5e-11)
        self.assertAlmostEqual(result.velocity.vx_mps, 1)
