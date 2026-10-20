"""Action timing boundaries and failure cases, without a compiler or solver."""
import copy
from dataclasses import replace
from decimal import Decimal, ROUND_CEILING, localcontext
from math import nextafter
import unittest

from warehouse_api.serialization import dumps, loads
from warehouse_api.contracts import ActionTimes, Drop, Lift, Pick, Serve, TaskAction
from warehouse_api.action_timing import action_duration_s, action_duration_ticks


# 中文: DurationTests 测试类验证共享动作耗时的数值边界与输入约束, 独立于求解器定位量化错误, 防止所有下游同时继承错误时长.
# English: DurationTests tests timing arithmetic and input constraints independently of solvers so a shared
# quantization bug cannot spread unnoticed to every planner.
class DurationTests(unittest.TestCase):
    # 中文: setUp 方法为每个测试新建耗时模型和多订单服务, 避免用例间共享状态, 提供可手算的数量基线.
    # English: setUp creates fresh timing settings and multi-order service for each test so cases stay
    # isolated and quantities remain easy to verify by hand.
    def setUp(self):
        self.times = ActionTimes(0.21, 0.3, 0.1, 0.1)
        self.serve = Serve("station", (Pick("A", "X", 1), Pick("B", "Y", 2)))

    # 中文: 本测试逐一核对取架, 服务和放架的离散时间步数 tick 与秒, 保证三个动作共用同一模型, 避免分支量化规则分叉.
    # English: This test checks discrete timestep counts (ticks) and seconds for lift, service and drop so all action branches obey the
    # same model and grid.
    def test_all_actions_share_model_and_grid(self):
        for action, ticks, seconds in ((Lift("shelf"), 3, 0.3),
                                       (self.serve, 4, 0.4),
                                       (Drop("storage"), 3, 0.3)):
            with self.subTest(action=action):
                self.assertEqual(action_duration_ticks(action, self.times, sim_dt_s=0.1), ticks)
                self.assertEqual(action_duration_s(action, self.times, sim_dt_s=0.1), seconds)

    # 中文: 本测试验证恰好落在十进制边界的耗时, 防止二进制浮点误差引入额外一拍, 改变服务计划.
    # English: This test checks exact decimal boundaries so binary floating-point error cannot introduce an
    # extra tick into the schedule.
    def test_exact_decimal_boundary_has_no_extra_tick(self):
        times = ActionTimes(0.07, 0.9, 0.1, 0.2)
        serve = Serve("station", (Pick("A", "X", 1),))
        self.assertEqual(action_duration_ticks(Lift("S"), times, sim_dt_s=0.01), 7)
        self.assertEqual(action_duration_ticks(serve, times, sim_dt_s=0.1), 3)
        self.assertEqual(action_duration_s(serve, times, sim_dt_s=0.1), 0.3)
        self.assertEqual(action_duration_s(Drop("P"), times, sim_dt_s=0.3), 0.9)

    # 中文: 本测试检查边界两侧的相邻浮点值, 防止 用容差 epsilon 把边界附近数值归到边界的处理把真实略超时长缩短到前一拍.
    # English: This test checks neighboring floats around a boundary so rounding nearby values onto a boundary with tolerance epsilon cannot shorten a
    # genuinely longer duration.
    def test_values_on_both_sides_of_boundary_are_not_snapped(self):
        for value, expected in ((nextafter(0.3, 0), 3), (0.3, 3),
                                (nextafter(0.3, 1), 4), (0.1 + 0.2, 4)):
            with self.subTest(value=value):
                times = replace(self.times, lift_s=value)
                self.assertEqual(action_duration_ticks(Lift("S"), times, sim_dt_s=0.1), expected)

    # 中文: 本测试比较拆分与合并的服务数量, 确认按总件数计时, 防止订单或商品种类标识 SKU 的分组方式影响耗时.
    # English: This test compares split and merged picks so service time depends on total units rather than
    # order grouping or grouping by product identifier (SKU).
    def test_service_sums_units_across_orders_and_repeated_skus(self):
        split = Serve("station", (Pick("A", "X", 1), Pick("A", "X", 2),
                                  Pick("B", "X", 4)))
        merged = Serve("station", (Pick("C", "X", 7),))
        for action in (split, merged):
            self.assertEqual(action_duration_ticks(action, self.times, sim_dt_s=0.3), 3)
            self.assertEqual(action_duration_s(action, self.times, sim_dt_s=0.3), 0.9)

    # 中文: 本测试覆盖零耗时和整数输入, 明确允许的边界行为, 防止校验过严拒绝合法模型.
    # English: This test covers zero durations and integer settings so boundary validation does not reject
    # supported timing models.
    def test_zero_durations_and_integer_inputs(self):
        for action in (Lift("S"), self.serve, Drop("P")):
            self.assertEqual(action_duration_s(action, ActionTimes(0, 0, 0, 0), sim_dt_s=1), 0)
        self.assertEqual(action_duration_ticks(self.serve, ActionTimes(1, 2, 3, 4), sim_dt_s=2), 8)

    # 中文: 本测试用独立的十进制 Decimal 计算检查多种模型和步长, 验证结果是最小可行 tick 数, 避免只重复实现算法.
    # English: This test uses an independent decimal-arithmetic Decimal reference calculation across models and grids to check minimal valid
    # ticks rather than duplicate the implementation.
    def test_decimal_oracle_over_model_and_grid_combinations(self):
        # An independent Decimal calculation checks minimum-tick rounding.
        with localcontext() as context:
            context.prec = 60
            for base in (0, 0.07, 0.1, 0.3, 1.01):
                for per_unit in (0, 0.01, 0.2, 0.333):
                    for dt in (0.01, 0.1, 0.3, 1):
                        times = ActionTimes(0, 0, base, per_unit)
                        raw = Decimal(str(base)) + 3 * Decimal(str(per_unit))
                        grid = Decimal(str(dt))
                        expected = int((raw / grid).to_integral_value(rounding=ROUND_CEILING))
                        ticks = action_duration_ticks(self.serve, times, sim_dt_s=dt)
                        self.assertEqual(ticks, expected)
                        self.assertGreaterEqual(ticks * grid, raw)
                        if ticks:
                            self.assertLess((ticks - 1) * grid, raw)

    # 中文: 本测试对耗时参数和步长注入非法值, 确认在计算入口报出具体字段, 防止坏数值进入动作时间轴.
    # English: This test injects invalid durations and timesteps so diagnostics name the field before bad
    # values enter action schedules.
    def test_invalid_model_fields_and_grid(self):
        for name in ("lift_s", "drop_s", "service_base_s", "service_per_unit_s"):
            for value in (-1, True, "1", float("nan"), float("inf")):
                with self.subTest(name=name, value=value), self.assertRaisesRegex(ValueError, name):
                    action_duration_s(self.serve, replace(self.times, **{name: value}), sim_dt_s=0.1)
        for value in (0, -0.1, True, "1", float("nan"), float("inf")):
            with self.subTest(dt=value), self.assertRaisesRegex(ValueError, "sim_dt_s"):
                action_duration_ticks(self.serve, self.times, sim_dt_s=value)

    # 中文: 本测试检查动作类型, 判别标记和件数, 防止不合法服务被当成零耗时或其他动作处理.
    # English: This test checks action types, tags and quantities so invalid service is not treated as zero
    # duration or another action kind.
    def test_invalid_action_and_picks(self):
        with self.assertRaisesRegex(TypeError, "action"):
            action_duration_s(object(), self.times, sim_dt_s=0.1)
        for action in (Lift("S", kind="drop"), Serve("P", ()),
                       Drop("P", kind="lift")):
            with self.subTest(action=action), self.assertRaises(ValueError):
                action_duration_s(action, self.times, sim_dt_s=0.1)
        for quantity in (0, -1, True, 1.5):
            with self.subTest(quantity=quantity), self.assertRaisesRegex(ValueError, "quantity"):
                action_duration_s(Serve("P", (Pick("A", "X", quantity),)),
                                  self.times, sim_dt_s=0.1)

    # 中文: 本测试覆盖极小步长及巨大 tick 数, 区分可计算整数结果与不可表示的秒数, 防止溢出被隐藏.
    # English: This test covers tiny grids and huge tick counts so valid integer results remain distinct from
    # unrepresentable seconds and overflow stays visible.
    def test_large_ticks_subnormal_grid_and_seconds_overflow(self):
        tiny = ActionTimes(5e-324, 0, 0, 0)
        self.assertEqual(action_duration_ticks(Lift("S"), tiny, sim_dt_s=5e-324), 1)
        self.assertEqual(action_duration_s(Lift("S"), tiny, sim_dt_s=5e-324), 5e-324)
        huge = ActionTimes(1e308, 0, 0, 1e308)
        self.assertEqual(action_duration_ticks(Lift("S"), huge, sim_dt_s=1e-308), 10**616)
        self.assertEqual(action_duration_s(Lift("S"), huge, sim_dt_s=1e-308), 1e308)
        with self.assertRaises(OverflowError):
            action_duration_s(self.serve, huge, sim_dt_s=1)
        with self.assertRaises(OverflowError):
            action_duration_s(Lift("S"), replace(self.times, lift_s=10**1000), sim_dt_s=1)

    # 中文: 本测试比较原输入与 JSON 重放的耗时并检查输入不变, 证明计时函数是可重复的纯计算入口.
    # English: This test compares original and JSON-replayed durations while checking immutability so timing
    # remains a repeatable pure calculation.
    def test_inputs_and_json_replay_are_unchanged(self):
        original = copy.deepcopy((self.serve, self.times))
        replay = loads(TaskAction, dumps(self.serve))
        for action in (self.serve, replay):
            self.assertEqual(action_duration_s(action, self.times, sim_dt_s=0.1), 0.4)
        self.assertEqual((self.serve, self.times), original)


if __name__ == "__main__":
    unittest.main()
