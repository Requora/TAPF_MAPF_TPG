"""中文: 本模块验证基准工作量和证据结构, 避免性能数字来自漏算请求.
English: This module checks benchmark workloads and evidence so omitted queries cannot inflate performance.
"""
from unittest.mock import patch
import unittest
from .benchmark import main, measure, make_fleet
from warehouse_api.trajectory import PreparedTrajectory


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
            with patch('trajectory.benchmark.PreparedTrajectory', wraps=PreparedTrajectory) as prepare:
                result = measure(fleet, 10, operation, frames=2, repeats=2)
            self.assertEqual(prepare.call_count, len(fleet))
            self.assertEqual(result['timed_calls'], 8)
            self.assertEqual(len(result['frame_ms']), 4)
            self.assertEqual(result['period_ms'], 100)
            self.assertLess(result['max_position_error_m'], 1e-10)
            self.assertGreater(result['median_frame_ms'], 0)
            self.assertNotIn('prepared', result)

    # 中文: 本测试要求基准在非 Linux 上先明确拒绝, 避免访问平台专属文件或执行测量.
    # English: This test requires the benchmark to reject non-Linux hosts before platform-specific reads or measurements.
    def test_non_linux_is_rejected_before_measurement(self):
        for system in ('Darwin', 'Windows'):
            with self.subTest(system=system), patch('sys.argv', ['benchmark', '--output', 'unused.json']), \
                    patch('trajectory.benchmark.platform.system', return_value=system), \
                    patch('trajectory.benchmark.Path.read_text', side_effect=AssertionError('Linux file read')), \
                    self.assertRaisesRegex(SystemExit, '2'):
                main()

    # 中文: 本测试拒绝已删除的模式开关, 防止基准重新出现第二条准备路径.
    # English: This test rejects the removed mode flag so the benchmark cannot regain a second preparation path.
    def test_removed_mode_flag_is_rejected(self):
        with patch('sys.argv', ['benchmark', '--prepared', '--output', 'unused.json']), \
                patch('trajectory.benchmark.Path.read_text', side_effect=AssertionError('Measurement started')), \
                self.assertRaisesRegex(SystemExit, '2'):
            main()
