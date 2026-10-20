"""Demand release and generation checks, without a runtime or solver."""
import copy
from dataclasses import replace
import random
import unittest

from warehouse_api.serialization import dumps, loads
from warehouse_api.contracts import Item, Order, OrderSource
from warehouse_api.order_source import ReplayOrderSource, generate_orders


class OrderSourceTests(unittest.TestCase):
    def setUp(self):
        self.orders = (
            Order("B", 2.0, (Item("Y", 1), Item("X", 2), Item("X", 3)), None),
            Order("A", 2.0, (Item("X", 1),), 1.0),
            Order("Z", 0.0, (Item("Y", 2),), None),
        )

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

    def test_inputs_are_unchanged_and_instances_are_independent(self):
        before = copy.deepcopy(self.orders)
        first = ReplayOrderSource(self.orders)
        second = ReplayOrderSource(self.orders)
        first.release(10.0)
        self.assertEqual(self.orders, before)
        self.assertEqual(second.release(0.0), (self.orders[2],))


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.parameters = dict(seed=17, count=12, skus=("Y", "X", "Z"),
                               release_interval_s=2.0, max_quantity=3, due_after_s=5.0)

    def test_seed_replay_and_global_random_state_isolation(self):
        state = random.getstate()
        first = generate_orders(**self.parameters)
        self.assertEqual(random.getstate(), state)
        self.assertEqual(generate_orders(**self.parameters), first)
        self.assertEqual(generate_orders(**{**self.parameters, "skus": ("Z", "Y", "X")}), first)
        self.assertNotEqual(generate_orders(**{**self.parameters, "seed": 18}), first)

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

    def test_empty_zero_interval_and_disabled_deadlines(self):
        self.assertEqual(generate_orders(seed=0, count=0, skus=("X",)), ())
        orders = generate_orders(seed=0, count=12, skus=("X",),
                                 release_interval_s=0, max_quantity=1)
        self.assertTrue(all(order.released_at_s == 0 and order.due_at_s is None
                            and order.items == (Item("X", 1),) for order in orders))
        source = ReplayOrderSource(orders)
        self.assertEqual(tuple(order.id for order in source.release(0)),
                         tuple(sorted(order.id for order in orders)))

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
