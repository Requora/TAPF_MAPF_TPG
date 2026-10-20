import copy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from .replay import compare, scenario
from ._validation import check_schedule


# 中文: ScheduleTests 用错误路径检验实验的离散检查, 防止上游成功退出被误作有效路线.
# English: ScheduleTests challenges the experiment's discrete checks so a successful exit cannot stand in for valid routes.
class ScheduleTests(unittest.TestCase):
    # 中文: setUp 提供两条独立合法路线, 让每次测试只改变一个约束.
    # English: setUp supplies two valid independent routes so each test changes one constraint.
    def setUp(self):
        self.case = scenario()
        self.output = {"statistics": {"cost": 6, "makespan": 3}, "schedule": {
            "agent0": [{"x": x, "y": 0, "t": x} for x in range(4)],
            "agent1": [{"x": x, "y": 0, "t": x - 1} for x in range(1, 5)],
        }}

    # 中文: 本测试核对有效路径的目标和代价, 让检查器也能明确接受正确结果.
    # English: This test checks goals and cost for valid routes so the checker demonstrably accepts correct results.
    def test_valid_schedule(self):
        self.assertEqual(check_schedule(self.case, self.output), [[3, 0], [4, 0]])

    # 中文: 本测试拒绝复用非空证据目录, 避免失败重跑后旧成功重放仍被展示.
    # English: This test rejects reused nonempty evidence directories so a failed rerun cannot leave an old success replay on display.
    def test_existing_evidence_is_not_overwritten(self):
        with TemporaryDirectory() as directory:
            replay = Path(directory) / "replay.html"
            replay.write_text("previous evidence")
            with self.assertRaises(FileExistsError):
                compare(Path("/nonexistent-binaries"), Path(directory))
            self.assertEqual(replay.read_text(), "previous evidence")

    # 中文: 本测试改变目标, 时间, 邻接关系和统计值, 防止归一化过程隐藏无效输出.
    # English: This test changes goals, time, adjacency and statistics so normalization cannot hide invalid output.
    def test_invalid_output_is_rejected(self):
        mutations = [
            ("agent0", 3, "x", 2), ("agent0", 1, "t", 2),
            ("agent0", 1, "x", 2), ("agent0", 1, "y", 1),
        ]
        for agent, index, field, value in mutations:
            with self.subTest(mutation=(agent, index, field, value)):
                output = copy.deepcopy(self.output)
                output["schedule"][agent][index][field] = value
                with self.assertRaises(ValueError):
                    check_schedule(self.case, output)
        self.output["statistics"]["cost"] = 7
        with self.assertRaisesRegex(ValueError, "cost"):
            check_schedule(self.case, self.output)

    # 中文: 本测试在短路径结束后制造碰撞, 确认已到达的机器人仍占据目标点.
    # English: This test creates a collision after a short route ends so arrived robots retain goal occupancy.
    def test_terminal_occupancy_is_checked(self):
        self.case["agents"][0]["potentialGoals"] = [[0, 0]]
        self.case["agents"][1]["potentialGoals"] = [[0, 0]]
        self.output["schedule"] = {
            "agent0": [{"x": 0, "y": 0, "t": 0}],
            "agent1": [{"x": 1, "y": 0, "t": 0}, {"x": 0, "y": 0, "t": 1}],
        }
        with self.assertRaisesRegex(ValueError, "vertex"):
            check_schedule(self.case, self.output)

    # 中文: 本测试交换相邻机器人的位置, 防止仅检查顶点而漏掉对向边冲突.
    # English: This test swaps adjacent robots so vertex-only checks cannot miss opposing edge traversal.
    def test_edge_swap_is_checked(self):
        self.case["agents"][0]["potentialGoals"] = [[1, 0]]
        self.case["agents"][1]["potentialGoals"] = [[0, 0]]
        self.output["schedule"] = {
            "agent0": [{"x": 0, "y": 0, "t": 0}, {"x": 1, "y": 0, "t": 1}],
            "agent1": [{"x": 1, "y": 0, "t": 0}, {"x": 0, "y": 0, "t": 1}],
        }
        with self.assertRaisesRegex(ValueError, "edge swap"):
            check_schedule(self.case, self.output)


# 中文: NativeComparisonTests 运行固定版本上游, 检查联合求解与所有固定分配的实际代价.
# English: NativeComparisonTests runs pinned upstream binaries to compare joint search with every fixed assignment.
@unittest.skipUnless(os.environ.get("WAREHOUSE_TAPF_BIN"), "set WAREHOUSE_TAPF_BIN for real CBS-TA")
class NativeComparisonTests(unittest.TestCase):
    # 中文: 本测试要求联合结果达到两种固定分配中的最小代价, 并检查原生调用证据.
    # English: This test requires the joint result to match the best of both fixed assignments and checks native evidence.
    def test_real_joint_search_matches_enumerated_assignments(self):
        with TemporaryDirectory() as directory:
            result = compare(Path(os.environ["WAREHOUSE_TAPF_BIN"]), Path(directory))
            self.assertEqual(sorted(row["statistics"]["cost"] for row in result["fixed"]), [6, 8])
            self.assertEqual(result["joint"]["statistics"]["cost"], 6)
            self.assertEqual(result["assignment"]["cost"], 6)
            records = list(Path(directory).glob("*.run.json"))
            self.assertEqual(len(records), 4)
            self.assertTrue(all(json.loads(path.read_text())["exit_code"] == 0 for path in records))
            self.assertEqual(json.loads((Path(directory) / "comparison.json").read_text()), result)
