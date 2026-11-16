"""中文: 本测试使用真实求解器验证控制帧链路, 单独标明可选原生依赖.
English: This test verifies the frame chain with real solvers and explicitly marks optional native dependencies.
"""
import os
from pathlib import Path
import unittest

from execution.replay import replay


# 中文: NativeExecutionTests 检查真实轨迹驱动下的全部动作启动和停车结果, 避免仅用 fixture 宣称集成完成.
# English: NativeExecutionTests checks native-driven starts and stopping instead of claiming integration from fixtures alone.
@unittest.skipUnless(os.environ.get('WAREHOUSE_NATIVE_BIN'), 'Optional native solver binaries are not configured')
class NativeExecutionTests(unittest.TestCase):
    # 中文: test_native_order_reaches_frames 检查真实订单产生三次独立动作启动并到达归还位置, 不声称动作完成或账本更新.
    # English: test_native_order_reaches_frames checks three distinct starts and arrival at the return node without claiming action completion or ledger updates.
    def test_native_order_reaches_frames(self):
        evidence = replay(Path(os.environ['WAREHOUSE_NATIVE_BIN']))
        self.assertEqual([row[2].step_index for row in evidence['action_starts']], [0, 1, 2])
        final = evidence['final_state'].robots[0]
        self.assertEqual(final.pose.x_m, 5)
        self.assertEqual(final.velocity.vx_mps, 0)
        self.assertGreater(evidence['frames'][-1]['frame'].from_s, 8.8)
