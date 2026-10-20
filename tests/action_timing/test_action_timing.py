"""Action timing boundaries and failure cases, without a compiler or solver."""
import copy
from dataclasses import replace
from decimal import Decimal, ROUND_CEILING, localcontext
from math import nextafter
import unittest

from warehouse_api.serialization import dumps, loads
from warehouse_api.contracts import ActionTimes, Drop, Lift, Pick, Serve, TaskAction
from warehouse_api.action_timing import action_duration_s, action_duration_ticks


class DurationTests(unittest.TestCase):
    def setUp(self):
        self.times = ActionTimes(0.21, 0.3, 0.1, 0.1)
        self.serve = Serve("station", (Pick("A", "X", 1), Pick("B", "Y", 2)))

    def test_all_actions_share_model_and_grid(self):
        for action, ticks, seconds in ((Lift("shelf"), 3, 0.3),
                                       (self.serve, 4, 0.4),
                                       (Drop("storage"), 3, 0.3)):
            with self.subTest(action=action):
                self.assertEqual(action_duration_ticks(action, self.times, sim_dt_s=0.1), ticks)
                self.assertEqual(action_duration_s(action, self.times, sim_dt_s=0.1), seconds)

    def test_exact_decimal_boundary_has_no_extra_tick(self):
        times = ActionTimes(0.07, 0.9, 0.1, 0.2)
        serve = Serve("station", (Pick("A", "X", 1),))
        self.assertEqual(action_duration_ticks(Lift("S"), times, sim_dt_s=0.01), 7)
        self.assertEqual(action_duration_ticks(serve, times, sim_dt_s=0.1), 3)
        self.assertEqual(action_duration_s(serve, times, sim_dt_s=0.1), 0.3)
        self.assertEqual(action_duration_s(Drop("P"), times, sim_dt_s=0.3), 0.9)

    def test_values_on_both_sides_of_boundary_are_not_snapped(self):
        for value, expected in ((nextafter(0.3, 0), 3), (0.3, 3),
                                (nextafter(0.3, 1), 4), (0.1 + 0.2, 4)):
            with self.subTest(value=value):
                times = replace(self.times, lift_s=value)
                self.assertEqual(action_duration_ticks(Lift("S"), times, sim_dt_s=0.1), expected)

    def test_service_sums_units_across_orders_and_repeated_skus(self):
        split = Serve("station", (Pick("A", "X", 1), Pick("A", "X", 2),
                                  Pick("B", "X", 4)))
        merged = Serve("station", (Pick("C", "X", 7),))
        for action in (split, merged):
            self.assertEqual(action_duration_ticks(action, self.times, sim_dt_s=0.3), 3)
            self.assertEqual(action_duration_s(action, self.times, sim_dt_s=0.3), 0.9)

    def test_zero_durations_and_integer_inputs(self):
        for action in (Lift("S"), self.serve, Drop("P")):
            self.assertEqual(action_duration_s(action, ActionTimes(0, 0, 0, 0), sim_dt_s=1), 0)
        self.assertEqual(action_duration_ticks(self.serve, ActionTimes(1, 2, 3, 4), sim_dt_s=2), 8)

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

    def test_invalid_model_fields_and_grid(self):
        for name in ("lift_s", "drop_s", "service_base_s", "service_per_unit_s"):
            for value in (-1, True, "1", float("nan"), float("inf")):
                with self.subTest(name=name, value=value), self.assertRaisesRegex(ValueError, name):
                    action_duration_s(self.serve, replace(self.times, **{name: value}), sim_dt_s=0.1)
        for value in (0, -0.1, True, "1", float("nan"), float("inf")):
            with self.subTest(dt=value), self.assertRaisesRegex(ValueError, "sim_dt_s"):
                action_duration_ticks(self.serve, self.times, sim_dt_s=value)

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

    def test_inputs_and_json_replay_are_unchanged(self):
        original = copy.deepcopy((self.serve, self.times))
        replay = loads(TaskAction, dumps(self.serve))
        for action in (self.serve, replay):
            self.assertEqual(action_duration_s(action, self.times, sim_dt_s=0.1), 0.4)
        self.assertEqual((self.serve, self.times), original)


if __name__ == "__main__":
    unittest.main()
