"""Shape checks only; fixtures are not solver or safety evidence."""
import copy
import dataclasses
import json
from pathlib import Path
import unittest

from warehouse_api import contracts as c
from warehouse_api.serialization import dumps, from_data, loads, to_data


FIXTURES = Path(__file__).parent / "fixtures"


# 中文: CodecTests 测试类验证统一契约的 JSON 结构转换, 将类型完整性与业务安全分开, 防止序列化成功被误解为方案合法.
# English: CodecTests tests JSON shape conversion separately from business safety so successful serialization is
# not mistaken for a valid executable plan.
class CodecTests(unittest.TestCase):
    # 中文: 本测试使用参考任务和路线数据做往返转换, 保护既有契约格式, 防止编解码器改变模块间共享的消息结构.
    # English: This test round-trips reference task and route fixtures so codec changes cannot silently alter
    # public message shapes.
    def test_selected_reference_fixtures_roundtrip(self):
        for name, cls in (("task_delta", c.TaskDelta), ("fleet_plan", c.FleetPlan)):
            with self.subTest(name=name):
                text = (FIXTURES / f"{name}.json").read_text(encoding="utf-8")
                value = loads(cls, text)
                self.assertEqual(to_data(value), json.loads(text))
                self.assertEqual(loads(cls, dumps(value)), value)
                self.assertIsInstance(value, cls)

    # 中文: 本测试覆盖所有业务动作和路线步骤分支, 验证用于识别动作类型的缺省判别字段恢复, 防止某一联合类型分支无法重放.
    # English: This test covers every action and route variant, including default tags that identify action types, so each union branch
    # remains replayable.
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

    # 中文: 本测试区分可空字段和可省略字段, 防止因类型包含 None 就接受缺失数据, 保留明确契约边界.
    # English: This test distinguishes nullable fields from defaulted fields so accepting None does not
    # accidentally permit omitted required data.
    def test_optional_is_required_unless_defaulted(self):
        order = c.Order("订单", 0.0, (c.Item("X", 2),), None)
        self.assertEqual(loads(c.Order, dumps(order)), order)
        data = to_data(order)
        del data["due_at_s"]
        with self.assertRaisesRegex(ValueError, r"\$\.due_at_s: missing"):
            from_data(c.Order, data)
        self.assertEqual(from_data(c.Lift, {"object_id": "P"}), c.Lift("P"))

    # 中文: 本测试修改编解码前后的容器并检查原对象, 确认没有别名共享, 防止保存或重放改变候选快照.
    # English: This test mutates input and output containers to check isolation so persistence and replay
    # cannot change a candidate through shared aliases.
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

    # 中文: 本测试在嵌套商品字段制造错误, 确认诊断保留完整路径, 让用户能直接定位坏输入.
    # English: This test injects nested item errors and checks full diagnostic paths so malformed input can be
    # located directly.
    def test_nested_field_diagnostics(self):
        order = {"id": "O", "released_at_s": 0, "items": [{"sku": "X", "quantity": True}],
                 "due_at_s": None}
        with self.assertRaisesRegex(ValueError, r"\$\.items\[0\]\.quantity: expected int"):
            from_data(c.Order, order)
        order["items"][0] = {"sku": "X", "quantity": 1, "extra": 1}
        with self.assertRaisesRegex(ValueError, r"\$\.items\[0\]: unknown fields.*extra"):
            from_data(c.Order, order)

    # 中文: 本测试检查布尔值, 字符串和数值不会被任意转换, 保持严格边界, 防止看似成功的解码掩盖输入错误.
    # English: This test checks that booleans, strings and numbers are not arbitrarily coerced so successful
    # decoding cannot conceal wrong input types.
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

    # 中文: 本测试验证系统拒绝错误标签和混合动作字段, 防止联合类型选错分支后改变任务含义.
    # English: This test checks rejection of invalid tags and mixed variant fields so union selection cannot change task
    # meaning by choosing the wrong branch.
    def test_invalid_discriminators_and_mixed_variants(self):
        for data in ({"object_id": "P", "kind": "move"},
                     {"object_id": "P", "kind": True},
                     {"object_id": "P", "station_id": "S", "picks": []}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                from_data(c.TaskAction, data)

    # 中文: 本测试覆盖 JSON 特殊数值和巨大整数, 保证非有限数被拒绝且溢出原样抛出, 保护后续物理计算.
    # English: This test covers special JSON numbers and huge integers so nonfinite data is rejected and
    # original overflow errors protect later physical arithmetic.
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

    # 中文: 本测试验证联合类型内的真实字段错误不被吞掉, 保持可追踪异常, 避免误报成模糊的分支不匹配.
    # English: This test checks that a selected union branch retains its real field error instead of being
    # reduced to a vague branch mismatch.
    def test_union_preserves_selected_branch_error(self):
        data = {"station_id": "S", "picks": [{"order_id": "O", "sku": "X", "quantity": True}]}
        with self.assertRaisesRegex(ValueError, r"^\$\.picks\[0\]\.quantity: expected int$"):
            from_data(c.TaskAction, data)
        with self.assertRaises(OverflowError):
            from_data(float | None, 10**400)
        self.assertEqual(from_data(float | None, 2), 2.0)
        self.assertEqual(from_data(c.Pose2 | None, {"x_m": 0, "y_m": 0, "yaw_rad": 0}),
                         c.Pose2(0.0, 0.0, 0.0))

    # 中文: 本测试往返各模块的成功或失败结果, 保证模块间共享的成功或失败 Result 类型可序列化, 让跨模块诊断也能重放.
    # English: This test round-trips success/failure result types shared between modules so module outputs and diagnostics can
    # both be replayed.
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

    # 中文: 本测试验证系统拒绝任意嵌套层的重复 JSON 键, 防止默认覆盖行为把矛盾字段悄悄隐藏.
    # English: This test checks rejection of duplicate JSON keys at any depth so parser overwrite behavior cannot hide
    # contradictory fields.
    def test_duplicate_keys_at_any_depth(self):
        for text in ('{"x_m":0,"x_m":1,"y_m":0}',
                     '{"tasks":[{"id":"A","id":"B","steps":[]}],"queues":[]}',
                     '{"x_m":0,"x_\\u006d":1,"y_m":0}'):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "Duplicate JSON field"):
                loads(c.TaskDelta, text)

    # 中文: 本测试确认解码器保留损坏 JSON 的原始解析异常, 让语法错误在入口显现, 不伪装为业务失败.
    # English: This test checks preservation of parser errors for malformed JSON so syntax failures stay visible at input
    # rather than masquerading as business failures.
    def test_malformed_json(self):
        for text in ('{"x_m":0,}', '{} {}', ''):
            with self.subTest(text=text), self.assertRaises(ValueError):
                loads(c.Point2, text)

    # 中文: 本测试验证系统拒绝编码时会丢失类型含义的键和值, 防止生成无法忠实恢复的重放文件.
    # English: This test checks rejection of keys and values that would lose meaning during encoding so replay files remain
    # faithful to their source data.
    def test_encoder_rejects_lossy_keys_and_unsupported_values(self):
        with self.assertRaises(ValueError):
            dumps({1: "number", "1": "string"})
        for value in (object(), {"set"}, c.Point2):
            with self.subTest(value=value), self.assertRaises(TypeError):
                dumps(value)

    # 中文: 本测试明确结构正确的非法业务数据仍可解码, 防止把 JSON 编解码器 codec 当作库存, ID 或几何合法性验证器.
    # English: This test shows that structurally valid but semantically invalid data can decode so the JSON codec is
    # not mistaken for inventory, ID or geometry validation.
    def test_shape_checks_do_not_claim_semantic_validation(self):
        self.assertEqual(loads(c.Item, '{"sku":"X","quantity":-1}'), c.Item("X", -1))
        self.assertEqual(loads(c.ObjectState,
                               '{"object_id":"P","ground_pose":null,"carrier_id":null}'),
                         c.ObjectState("P", None, None))


if __name__ == "__main__":
    unittest.main()
