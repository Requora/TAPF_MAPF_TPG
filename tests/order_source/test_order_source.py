"""Demand release and generation checks, without a runtime or solver."""
import copy
from dataclasses import replace
import random
import unittest

from warehouse_api.serialization import dumps, loads
from warehouse_api.contracts import Item, Order, OrderSource
from warehouse_api.order_source import ReplayOrderSource, generate_orders


# 中文: 覆盖订单发布和重置语义, 防止重复需求或状态污染, 为后续分配提供可信发布序列.
# English: Test order release and reset semantics so allocation receives a reliable sequence without
# duplicate demand or contaminated state.
class OrderSourceTests(unittest.TestCase):
    # 中文: 构造乱序时间和重复 SKU 的订单, 让归一化与同刻排序在每个测试中可被明确检验.
    # English: Build orders with unordered times and repeated SKUs so normalization and equal-time
    # ordering are explicit in every test.
    def setUp(self):
        self.orders = (
            Order("B", 2.0, (Item("Y", 1), Item("X", 2), Item("X", 3)), None),
            Order("A", 2.0, (Item("X", 1),), 1.0),
            Order("Z", 0.0, (Item("Y", 2),), None),
        )

    # 中文: 验证截止时刻包含边界, SKU合并且订单只发布一次, 防止同一需求被多次交给分配器.
    # English: Check inclusive deadlines, SKU merging and one-time release so allocation never
    # receives the same demand twice.
    def test_inclusive_ordering_merging_and_no_duplicates(self):
        source: OrderSource = ReplayOrderSource(self.orders)
        self.assertEqual(source.release(0.0), (self.orders[2],))
        self.assertEqual(source.release(0.0), ())
        self.assertEqual(source.release(1.999), ())
        released = source.release(2.0)
        self.assertEqual(tuple(order.id for order in released), ("A", "B"))
        self.assertEqual(released[1].items, (Item("X", 5), Item("Y", 1)))
        self.assertEqual(released[0].due_at_s, 1.0)
        self.assertEqual(source.release(2.0), ())
        self.assertEqual(source.release(100.0), ())

    # 中文: 验证重置能重放, 替换和清空序列, 保证实验重启不继承旧游标或剩余订单.
    # English: Check replay, replacement and clearing through reset so restarted experiments do not
    # inherit old cursors or orders.
    def test_reset_replays_and_replaces_schedule(self):
        source = ReplayOrderSource(self.orders)
        first = source.release(10.0)
        source.reset(self.orders)
        self.assertEqual(source.release(10.0), first)
        source.reset((self.orders[2],))
        self.assertEqual(source.release(0.0), (self.orders[2],))
        self.assertEqual(source.release(10.0), ())
        source.reset(())
        self.assertEqual(source.release(0.0), ())
        self.assertEqual(ReplayOrderSource().release(0.0), ())

    # 中文: 在错误发布时间之后继续正常发布, 验证失败不推进游标, 避免订单被悄悄跳过.
    # English: Resume release after invalid times to check that failed calls preserve the cursor and
    # do not silently skip orders.
    def test_backward_and_invalid_times_preserve_cursor(self):
        source = ReplayOrderSource(self.orders)
        source.release(1.0)
        for value in (0.5, -1.0, float("nan"), float("inf"), True, "2"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                source.release(value)
        self.assertEqual(tuple(order.id for order in source.release(2.0)), ("A", "B"))
        source.release(10.0)
        with self.assertRaisesRegex(ValueError, "backward"):
            source.release(9.0)

    # 中文: 尝试用非法订单重置后重放旧序列, 确认校验先于状态替换, 防止半完成的重置污染实验.
    # English: Attempt invalid resets before replaying the old schedule so validation is confirmed
    # to precede any state replacement.
    def test_invalid_reset_preserves_existing_schedule_and_time(self):
        source = ReplayOrderSource(self.orders)
        source.release(1.0)
        order = self.orders[0]
        invalid = [replace(order, id=""), replace(order, id=" "),
                   replace(order, released_at_s=-1), replace(order, released_at_s=True),
                   replace(order, released_at_s=float("nan")),
                   replace(order, due_at_s=float("inf")), replace(order, due_at_s=-1),
                   replace(order, items=()), replace(order, items=(Item("", 1),))]
        invalid += [replace(order, items=(Item("X", value),))
                    for value in (0, -1, True, 1.5)]
        for bad in invalid:
            with self.subTest(order=bad), self.assertRaises(ValueError):
                source.reset((self.orders[2], bad))
        with self.assertRaisesRegex(ValueError, "Duplicate order ID"):
            source.reset((order, order))
        with self.assertRaisesRegex(ValueError, "backward"):
            source.release(0.0)
        self.assertEqual(tuple(order.id for order in source.release(2.0)), ("A", "B"))

    # 中文: 比较两个订单源及原始输入, 确认游标隔离, 防止一个实验的发布影响另一个实验.
    # English: Compare two sources and their input to ensure cursor isolation and prevent one
    # experiment from affecting another.
    def test_inputs_are_unchanged_and_instances_are_independent(self):
        before = copy.deepcopy(self.orders)
        first = ReplayOrderSource(self.orders)
        second = ReplayOrderSource(self.orders)
        first.release(10.0)
        self.assertEqual(self.orders, before)
        self.assertEqual(second.release(0.0), (self.orders[2],))


# 中文: 验证随机订单的 seed 和参数语义, 为可复现实验建立约束, 防止随机性掩盖规划回归.
# English: Test seeded generation and parameter semantics so reproducible demand can expose planner
# regressions instead of hiding them in randomness.
class GenerationTests(unittest.TestCase):
    # 中文: 固定一个含多 SKU 的生成配置, 作为对照实验基线, 让各测试只改变关注的参数.
    # English: Fix a multi-SKU generation configuration so each test changes only the parameter
    # under examination.
    def setUp(self):
        self.parameters = dict(seed=17, count=12, skus=("Y", "X", "Z"),
                               release_interval_s=2.0, max_quantity=3, due_after_s=5.0)

    # 中文: 核对同 seed 重现和全局随机状态不变, 防止订单生成影响其他随机算法的结果.
    # English: Check seeded replay and global RNG isolation so generating orders cannot perturb
    # other randomized algorithms.
    def test_seed_replay_and_global_random_state_isolation(self):
        state = random.getstate()
        first = generate_orders(**self.parameters)
        self.assertEqual(random.getstate(), state)
        self.assertEqual(generate_orders(**self.parameters), first)
        self.assertEqual(generate_orders(**{**self.parameters, "skus": ("Z", "Y", "X")}), first)
        self.assertNotEqual(generate_orders(**{**self.parameters, "seed": 18}), first)

    # 中文: 验证生成的 ID, 数量和时间后经 codec及订单源重放, 保证随机输出真正符合公共输入契约.
    # English: Check generated IDs, quantities and times through codec and release replay so
    # generated demand actually satisfies public contracts.
    def test_generated_contracts_and_release_replay(self):
        orders = generate_orders(**self.parameters)
        self.assertEqual(len(orders), 12)
        self.assertEqual(len({order.id for order in orders}), 12)
        for index, order in enumerate(orders):
            self.assertEqual(order.released_at_s, 2.0 * index)
            self.assertEqual(order.due_at_s, order.released_at_s + 5.0)
            self.assertTrue(order.items)
            self.assertEqual(tuple(item.sku for item in order.items),
                             tuple(sorted({item.sku for item in order.items})))
            for item in order.items:
                self.assertIn(item.sku, self.parameters["skus"])
                self.assertIn(item.quantity, range(1, 4))
        self.assertEqual(loads(tuple[Order, ...], dumps(orders)), orders)
        source = ReplayOrderSource(orders)
        observed = tuple(order for time in (0, 3, 3, 8, 30) for order in source.release(time))
        self.assertEqual(observed, orders)
        source.reset(orders)
        self.assertEqual(source.release(30), observed)

    # 中文: 覆盖空需求, 同刻发布和无截止配置, 明确合法退化情况, 避免生成器凭空补需求或时间.
    # English: Cover empty demand, simultaneous release and disabled due times so supported edge
    # cases do not invent orders or timing.
    def test_empty_zero_interval_and_disabled_deadlines(self):
        self.assertEqual(generate_orders(seed=0, count=0, skus=("X",)), ())
        orders = generate_orders(seed=0, count=12, skus=("X",),
                                 release_interval_s=0, max_quantity=1)
        self.assertTrue(all(order.released_at_s == 0 and order.due_at_s is None
                            and order.items == (Item("X", 1),) for order in orders))
        source = ReplayOrderSource(orders)
        self.assertEqual(tuple(order.id for order in source.release(0)),
                         tuple(sorted(order.id for order in orders)))

    # 中文: 逐项拒绝错误参数及末时刻溢出, 保证失败发生在生成前, 避免得到部分有效的订单序列.
    # English: Reject invalid settings and final-time overflow before generation so a configuration
    # cannot produce a partially valid schedule.
    def test_invalid_generation_parameters(self):
        cases = {"seed": (True, 1.5), "count": (-1, True, 1.5),
                 "skus": ((), ("X", "X"), (" ",), (1,), "XY"),
                 "release_interval_s": (-1, float("nan"), float("inf"), True),
                 "max_quantity": (0, -1, 1.5, True),
                 "due_after_s": (-1, float("inf"), True)}
        for name, values in cases.items():
            for value in values:
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    generate_orders(**{**self.parameters, name: value})
        for changes in ({"release_interval_s": 1e308},
                        {"count": 2, "release_interval_s": 1e308, "due_after_s": 1e308}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                generate_orders(**{**self.parameters, **changes})


if __name__ == "__main__":
    unittest.main()
