"""Shape checks only; fixtures are not solver or safety evidence."""
import copy
import dataclasses
import json
from pathlib import Path
import unittest

from warehouse_api import contracts as c
from warehouse_api.serialization import dumps, from_data, loads, to_data


FIXTURES = Path(__file__).parent / "fixtures"


class CodecTests(unittest.TestCase):
    def test_selected_reference_fixtures_roundtrip(self):
        for name, cls in (("task_delta", c.TaskDelta), ("fleet_plan", c.FleetPlan)):
            with self.subTest(name=name):
                text = (FIXTURES / f"{name}.json").read_text(encoding="utf-8")
                value = loads(cls, text)
                self.assertEqual(to_data(value), json.loads(text))
                self.assertEqual(loads(cls, dumps(value)), value)
                self.assertIsInstance(value, cls)

    def test_all_action_and_route_variants(self):
        actions = (c.Lift("P"), c.Serve("S", (c.Pick("O", "X", 2),)), c.Drop("L"))
        steps = (c.Move("E"), c.Turn(1.5), c.Do(c.StepRef("T", 0)))
        for cls, values in ((c.TaskAction, actions), (c.RouteStep, steps)):
            for value in values:
                with self.subTest(value=value):
                    self.assertEqual(loads(cls, dumps(value)), value)
                    data = to_data(value)
                    del data["kind"]
                    self.assertEqual(from_data(cls, data), value)

    def test_optional_is_required_unless_defaulted(self):
        order = c.Order("订单", 0.0, (c.Item("X", 2),), None)
        self.assertEqual(loads(c.Order, dumps(order)), order)
        data = to_data(order)
        del data["due_at_s"]
        with self.assertRaisesRegex(ValueError, r"\$\.due_at_s: missing"):
            from_data(c.Order, data)
        self.assertEqual(from_data(c.Lift, {"object_id": "P"}), c.Lift("P"))

    def test_input_and_output_are_independent(self):
        data = json.loads((FIXTURES / "task_delta.json").read_text())
        original = copy.deepcopy(data)
        value = from_data(c.TaskDelta, data)
        self.assertEqual(data, original)
        self.assertIsInstance(value.tasks, tuple)
        self.assertIsInstance(value.tasks[0].steps, tuple)
        data["tasks"][0]["id"] = "changed"
        encoded = to_data(value)
        encoded["queues"][0]["task_ids"].append("changed")
        self.assertEqual(to_data(value), original)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            value.tasks = ()

    def test_nested_field_diagnostics(self):
        order = {"id": "O", "released_at_s": 0, "items": [{"sku": "X", "quantity": True}],
                 "due_at_s": None}
        with self.assertRaisesRegex(ValueError, r"\$\.items\[0\]\.quantity: expected int"):
            from_data(c.Order, order)
        order["items"][0] = {"sku": "X", "quantity": 1, "extra": 1}
        with self.assertRaisesRegex(ValueError, r"\$\.items\[0\]: unknown fields.*extra"):
            from_data(c.Order, order)

    def test_wrong_types_are_not_coerced(self):
        cases = ((int, True), (int, 1.0), (str, 1), (bool, 1),
                 (float, True), (float, "1"), (type(None), 0),
                 (tuple[str, ...], "R1"), (c.Point2, []),
                 (c.Item, {"sku": "X", "quantity": 1, 2: 3}))
        for cls, data in cases:
            with self.subTest(cls=cls, data=data), self.assertRaises(ValueError):
                from_data(cls, data)
        self.assertEqual(from_data(float, 2), 2.0)
        self.assertIs(type(from_data(float, 2)), float)

    def test_invalid_discriminators_and_mixed_variants(self):
        for data in ({"object_id": "P", "kind": "move"},
                     {"object_id": "P", "kind": True},
                     {"object_id": "P", "station_id": "S", "picks": []}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                from_data(c.TaskAction, data)

    def test_nonfinite_and_overflow_numbers(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    dumps(c.Point2(value, 0.0))
                with self.assertRaises(ValueError):
                    from_data(c.Point2, {"x_m": value, "y_m": 0})
        for token in ("NaN", "Infinity", "-Infinity", "1e400", "-1e400"):
            with self.subTest(token=token), self.assertRaises(ValueError):
                loads(c.Point2, '{"x_m":' + token + ',"y_m":0}')
        with self.assertRaises(OverflowError):
            loads(c.Point2, '{"x_m":' + str(10**400) + ',"y_m":0}')

    def test_union_preserves_selected_branch_error(self):
        data = {"station_id": "S", "picks": [{"order_id": "O", "sku": "X", "quantity": True}]}
        with self.assertRaisesRegex(ValueError, r"^\$\.picks\[0\]\.quantity: expected int$"):
            from_data(c.TaskAction, data)
        with self.assertRaises(OverflowError):
            from_data(float | None, 10**400)
        self.assertEqual(from_data(float | None, 2), 2.0)
        self.assertEqual(from_data(c.Pose2 | None, {"x_m": 0, "y_m": 0, "yaw_rad": 0}),
                         c.Pose2(0.0, 0.0, 0.0))

    def test_public_result_unions(self):
        failure = c.Failure("BAD_INPUT", "invalid request", ())
        cases = ((c.TaskDelta | c.Failure, c.TaskDelta((), ())),
                 (c.FleetPlan | c.Failure, c.FleetPlan("Q", (), ())),
                 (c.MotionPlan | c.Failure, c.MotionPlan((), ())),
                 (c.ExecutableProposal | c.Failure,
                  c.ExecutableProposal("Q", c.TaskDelta((), ()), c.MotionPlan((), ()))),
                 (c.IdealControlFrame | c.Failure, c.IdealControlFrame(0.0, 1.0, (), ())),
                 (c.Observation | c.Failure, c.Observation(c.PhysicalState(0.0, (), (), ()), ())),
                 (c.Accepted | c.Failure, c.Accepted("C", 1)),
                 (tuple[c.RobotJobs, ...] | c.Failure, (c.RobotJobs("R", ()),)))
        for cls, value in cases:
            with self.subTest(cls=cls):
                self.assertEqual(loads(cls, dumps(value)), value)
                self.assertEqual(loads(cls, dumps(failure)), failure)

    def test_duplicate_keys_at_any_depth(self):
        for text in ('{"x_m":0,"x_m":1,"y_m":0}',
                     '{"tasks":[{"id":"A","id":"B","steps":[]}],"queues":[]}',
                     '{"x_m":0,"x_\\u006d":1,"y_m":0}'):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "Duplicate JSON field"):
                loads(c.TaskDelta, text)

    def test_malformed_json(self):
        for text in ('{"x_m":0,}', '{} {}', ''):
            with self.subTest(text=text), self.assertRaises(ValueError):
                loads(c.Point2, text)

    def test_encoder_rejects_lossy_keys_and_unsupported_values(self):
        with self.assertRaises(ValueError):
            dumps({1: "number", "1": "string"})
        for value in (object(), {"set"}, c.Point2):
            with self.subTest(value=value), self.assertRaises(TypeError):
                dumps(value)

    def test_shape_checks_do_not_claim_semantic_validation(self):
        self.assertEqual(loads(c.Item, '{"sku":"X","quantity":-1}'), c.Item("X", -1))
        self.assertEqual(loads(c.ObjectState,
                               '{"object_id":"P","ground_pose":null,"carrier_id":null}'),
                         c.ObjectState("P", None, None))


if __name__ == "__main__":
    unittest.main()
