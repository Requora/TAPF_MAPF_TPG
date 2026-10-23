"""中文: 本模块验证基准工作量和证据结构, 避免性能数字来自漏算请求.
English: This module checks benchmark workloads and evidence so omitted queries cannot inflate performance.
"""
import unittest
from .benchmark import measure, make_fleet


# 中文: BenchmarkTests 检查真实 API 调用数量与解析结果, 不对易波动的机器速度设断言.
# English: BenchmarkTests checks real API workload and analytic results without asserting noisy machine speed.
class BenchmarkTests(unittest.TestCase):
    # 中文: 本测试核对每轮车队查询及两个 API 的输出, 防止基准测量空循环或无效时间.
    # English: This test checks fleet queries and both API outputs so the benchmark cannot measure empty loops or invalid times.
    def test_workload_and_evidence(self):
        fleet = make_fleet(2, 4)
        self.assertIsNot(fleet[0], fleet[1])
        self.assertNotEqual(fleet[0][0].pose.y_m, fleet[1][0].pose.y_m)
        for operation in ('evaluate', 'slice_curve'):
            result = measure(fleet, 10, operation, frames=2, repeats=2)
            self.assertEqual(result['timed_calls'], 8)
            self.assertEqual(len(result['frame_ms']), 4)
            self.assertEqual(result['period_ms'], 100)
            self.assertLess(result['max_position_error_m'], 1e-10)
            self.assertGreater(result['median_frame_ms'], 0)
